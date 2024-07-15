# Markov

# Set the data needed to represent a Markov State Model grpah in the client
# This is finding the most populated frames and calculating an RMSD matrix between these frames

from typing import List
from os import remove

import mdtraj as mdt

from model_workflow.tools.get_screenshot import get_screenshot
from model_workflow.utils.auxiliar import save_json

auxiliar_pdb_filename = '.model.pdb'

def markov (
    input_topology_filename : str,
    input_trajectory_filename : str,
    output_analysis_filename : str,
    structure : 'Structure',
    populations : List[float],
    rmsd_selection : str,
    nodes_number : int = 20,
):

    # If there is no populations then we stop here
    if not populations or len(populations) == 0:
        print(' There are no populations')
        return

    # Parse the RMSD selection in VMD selection syntax
    parsed_selection = structure.select(rmsd_selection, syntax='vmd')
    # If there is nothing to check then warn the user and stop here
    if not parsed_selection:
        raise SystemExit('There are not atoms to be analyzed for the RMSD matrix')

    # Get the numbers of frames with highest populations
    population_per_frames = [ (population, frame) for frame, population in enumerate(populations) ]
    highest_populations = []
    highest_population_frames = []
    for population, frame in sorted(population_per_frames, reverse=True)[0:nodes_number]:
        highest_populations.append(population)
        highest_population_frames.append(frame)
    print(' Reading most populated frames in trajectory')
    # Read the trajectory frame by frame looking for the specified frames
    trajectory = mdt.iterload(input_trajectory_filename, top=input_topology_filename, chunk=1)
    # Set a generator for the frames to be selected once sorted
    selected_frames = iter(sorted(highest_population_frames))
    next_frame = next(selected_frames)
    # Conserve only the desired frames
    frame_coordinates = {}
    for frame_number, chunk in enumerate(trajectory):
        # Update the current frame log
        print(' Frame ' + str(frame_number), end='\r')
        # Skip the current frame if we do not need it
        if frame_number != next_frame:
            continue
        # Save it otherwise
        frame_coordinates[frame_number] = chunk
        # Update the next frame
        next_frame = next(selected_frames, None)
        if next_frame == None:
            break
    print(' Calculating RMSD matrix')
    # Calculate the RMSD matrix between the selected frames
    rmsd_matrix = []
    for x, frame in enumerate(highest_population_frames):
        rmsd_row = []
        for y, other_frame in enumerate(highest_population_frames):
            # RMSD of any frame against itself is 0
            if x == y:
                rmsd_row.append(0)
                continue
            # If RMSD was previously calculated in the opposite way then copy the value
            if x > y:
                rmsd_row.append(rmsd_matrix[y][x])
                continue
            # Otherwise calculate RMSD between the asked frames
            rsmd = mdt.rmsd(frame_coordinates[frame], frame_coordinates[other_frame], atom_indices=parsed_selection.atom_indices)[0]
            rmsd_row.append(float(rsmd))
        rmsd_matrix.append(rmsd_row)
    print(' Taking screenshots of selected frames')
    frame_count = str(len(frame_coordinates))
    # Save the screenshot parameters so we can keep images coherent between states
    screenshot_parameters = None
    # For each frame coordinates, generate PDB file, take a scrrenshot and delete it
    for i, coordinates in enumerate(frame_coordinates.values(), 1):
        # Update the current frame log
        print('  Screenshot ' + str(i) + '/' + frame_count, end='\r')
        # Generate the pdb file
        coordinates.save(auxiliar_pdb_filename)
        # Set the screenshot filename
        screenshot_filename = 'markov_screenshot_' + str(i).zfill(2) + '.jpg'
        # Generate the screenshot
        screenshot_parameters = get_screenshot(auxiliar_pdb_filename, screenshot_filename, parameters=screenshot_parameters)
        # Remove the pdb file
        remove(auxiliar_pdb_filename)
    # Export the analysis data to a json file
    data = {
        'frames': highest_population_frames,
        'populations': highest_populations,
        'rmsd_matrix': rmsd_matrix
    }
    save_json(data, output_analysis_filename)