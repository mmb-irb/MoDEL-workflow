from subprocess import run, PIPE, Popen
from model_workflow.tools.get_reduced_trajectory import get_reduced_trajectory

# Radius of gyration (Rgyr)
# 
# Perform the RMSd analysis 
# Use the first trajectory frame in .pdb format as a reference
def rgyr (
    input_topology_filename : str,
    input_trajectory_filename : str,
    output_analysis_filename : str,
    frames_limit : int) -> str:

    # Use a reduced trajectory in case the original trajectory has many frames
    reduced_trajectory_filename, step, frames = get_reduced_trajectory(
        input_topology_filename,
        input_trajectory_filename,
        frames_limit,
    )
    
    # Run Gromacs
    p = Popen([
        "echo",
        "Protein",
    ], stdout=PIPE)
    logs = run([
        "gmx",
        "gyrate",
        "-s",
        input_topology_filename,
        "-f",
        reduced_trajectory_filename,
        '-o',
        output_analysis_filename,
        '-quiet'
    ], stdin=p.stdout, stdout=PIPE).stdout.decode()
    p.stdout.close()

    # Return gromacs logs
    return logs