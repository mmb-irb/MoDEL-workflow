import tmscoring

from subprocess import run, PIPE, Popen
import json

from model_workflow.tools.get_pdb_frames import get_pdb_frames

# TM scores
# 
# Perform the tm score using the tmscoring package
def tmscores (
    input_topology_filename : str,
    input_trajectory_filename : str,
    output_analysis_filename : str,
    first_frame_filename : str,
    average_structure_filename : str):

    tmscore_references  = [first_frame_filename, average_structure_filename]

    start = 0
    step = None

    # Set a maximum of frames
    frames_limit = 200
    
    output_analysis = []

    # The only possible group in TM score is the alpha carbon
    # They are the only atoms taken in count by the TM score algorithm
    group = 'C-alpha'

    # Get a standarized group name
    group_name = 'c-alpha'

    frames_ndx = 'frames.ndx'
    # Iterate over each reference and group
    for reference in tmscore_references:
        # Get a standarized reference name
        reference_name = reference[0:-4].lower()
        # Create a reference topology with only the group atoms
        # WARNING: Yes, TM score would work also with the whole reference, but it takes more time!!
        # This has been experimentally tested and it may take more than the double of time
        grouped_reference = 'gref.pdb'
        p = Popen([
            "echo",
            group,
        ], stdout=PIPE)
        logs = run([
            "gmx",
            "trjconv",
            "-s",
            reference,
            "-f",
            reference,
            '-o',
            grouped_reference,
            "-dump",
            "0",
            '-quiet'
        ], stdin=p.stdout, stdout=PIPE).stdout.decode()
        p.stdout.close()
        # Get the TM score of each frame
        # It must be done this way since tmscoring does not support trajectories
        tmscores = []
        frames, step, count = get_pdb_frames(reference, input_trajectory_filename, frames_limit)
        for current_frame in frames:

            # Filter atoms in the current frame
            p = Popen([
                "echo",
                group,
            ], stdout=PIPE)
            logs = run([
                "gmx",
                "trjconv",
                "-s",
                current_frame,
                "-f",
                current_frame,
                '-o',
                current_frame,
                '-quiet'
            ], stdin=p.stdout, stdout=PIPE).stdout.decode()
            p.stdout.close()

            # Run the tmscoring over the current frame against the current reference
            # Append the result data for each ligand
            tmscore = tmscoring.get_tm(grouped_reference, current_frame)
            tmscores.append(tmscore)

        # Save the tmscores in the output object
        data = {
            'values': tmscores,
            'reference': reference_name,
            'group': group_name
        }
        output_analysis.append(data)

        run([
            "rm",
            grouped_reference,
        ], stdout=PIPE).stdout.decode()

    # Export the analysis in json format
    with open(output_analysis_filename, 'w') as file:
        json.dump({ 'start': start, 'step': step, 'data': output_analysis }, file)