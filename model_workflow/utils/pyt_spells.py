import pytraj as pyt
import math
from distutils.version import StrictVersion
from typing import Optional

from model_workflow.utils.auxiliar import InputError
from model_workflow.utils.selections import Selection

# Set pytraj supported formats
pytraj_supported_structure_formats = {'prmtop', 'pdb', 'mol2', 'psf', 'cif', 'sdf'}
pytraj_supported_trajectory_formats = {'xtc', 'trr', 'crd', 'mdcrd', 'nc', 'dcd'}

# Get the whole trajectory as a generator
def get_pytraj_trajectory (
    input_topology_filename : str,
    input_trajectory_filename : str,
    atom_selection : Optional['Selection'] = None):

    # Topology is mandatory to setup the pytraj trajectory
    if not input_topology_filename:
        raise SystemExit('Missing topology file to setup PyTraj trajectory')
    
    # Set the pytraj trayectory and get the number of frames
    # NEVER FORGET: The pytraj iterload does not accept a mask, but we can strip atomos later
    pyt_trajectory = pyt.iterload(input_trajectory_filename, input_topology_filename)
    
    # WARNING: This extra line prevents the error "Segment violation (core dumped)" in some pdbs
    # This happens with some random pdbs which pytraj considers to have 0 Mols
    # More info: https://github.com/Amber-MD/cpptraj/pull/820
    # DANI: Esto es útil en pytraj <= 2.0.5 pero hace fallar el código a partir de pytraj 2.0.6
    if StrictVersion(pyt.__version__) <= StrictVersion('2.0.5'):
        pyt_trajectory.top.start_new_mol()

    # Filter away atoms which ARE NOT in the atom selection
    if atom_selection:
        # Get atom indices for all atoms but the ones in the atom selection
        topology = pyt_trajectory.top
        all_atoms = set(range(topology.n_atoms))
        keep_atoms = set(atom_selection.atom_indices)
        strip_atoms = all_atoms - keep_atoms
        if len(strip_atoms) > 0:
            # Convert the strip atom indices to a pytraj mask string and strip the iterator
            mask = Selection(strip_atoms).to_pytraj()
            pyt_trajectory = pyt_trajectory.strip(mask)

    return pyt_trajectory

# Get the reduced trajectory
# WARNING: The final number of frames may be the specifided or less
def get_reduced_pytraj_trajectory (
    input_topology_filename : str,
    input_trajectory_filename : str,
    snapshots : int,
    reduced_trajectory_frames_limit : int):
    
    # Set the pytraj trayectory and get the number of frames
    pt_trajectory = get_pytraj_trajectory(input_topology_filename, input_trajectory_filename)
    # WARNING: Do not read pt_trajectory.n_frames to get the number of snapshots or you will read the whole trajectory
    # WARNING: This may be a lot of time for a huge trajectory. Use the snapshots input instead

    # Set a reduced trajectory used for heavy analyses

    # If the current trajectory has already less or the same frames than the limit
    # Then do nothing and use it also as reduced
    if snapshots <= reduced_trajectory_frames_limit:
        frame_step = 1
        return pt_trajectory, frame_step, snapshots

    # Otherwise, create a reduced trajectory with as much frames as specified above
    # These frames are picked along the trajectory
    # Calculate the step between frames in the reduced trajectory to match the final number of frames
    # WARNING: Since the step must be an integer the thorical step must be rounded
    # This means the specified final number of frames may not be accomplished, but it is okey
    # WARNING: Since the step is rounded with the math.ceil function it will always be rounded up
    # This means the final number of frames will be the specified or less
    # CRITICAL WARNING:
    # This formula is exactly the same that the client uses to request stepped frames to the API
    # This means that the client and the workflow are coordinated and these formulas must not change
    # If you decide to change this formula (in both workflow and client)...
    # You will have to run again all the database analyses with reduced trajectories
    frame_step = math.ceil(snapshots / reduced_trajectory_frames_limit)
    reduced_pt_trajectory = pt_trajectory[0:snapshots:frame_step]
    reduced_frame_count = math.ceil(snapshots / frame_step)
    return reduced_pt_trajectory, frame_step, reduced_frame_count

# Get the trajectory frames number
# LORE: This was tried also with mdtraj's iterload but pytraj was way faster
def get_frames_count (
    input_topology_file : 'File',
    input_trajectory_file : 'File') -> int:
    
    print('-> Counting number of frames')

    if not input_trajectory_file.exists:
        raise InputError('Missing trajectroy file when counting frames: ' + input_trajectory_file.path)
    
    if not input_topology_file.exists:
        raise InputError('Missing topology file when counting frames: ' + input_topology_file.path)

    # Load the trajectory from pytraj
    pyt_trajectory = pyt.iterload(
        input_trajectory_file.path,
        input_topology_file.path)

    # Return the frames number
    frames = pyt_trajectory.n_frames
    print(' Frames: ' + str(frames))

    # If 0 frames were counted then there is something wrong with the file
    if frames == 0:
        raise InputError('Something went wrong when reading the trajectory')

    return frames
# Set function supported formats
get_frames_count.format_sets = [
    {
        'inputs': {
            'input_structure_filename': pytraj_supported_structure_formats,
            'input_trajectory_filename': pytraj_supported_trajectory_formats
        }
    }
]

# Filter topology atoms
# DANI: Note that a PRMTOP file is not a structure but a topology
# DANI: However it is important that the argument is called 'structure' for the format finder
def filter_topology (
    input_structure_file : str,
    output_structure_file : str,
    input_selection : 'Selection'
):
    # Generate a pytraj mask with the desired selection
    mask = input_selection.to_pytraj()

    # Load the topology
    topology = pyt.load_topology(input_structure_file.path)

    # Apply the filter mask
    filtered_topology = topology[mask]

    # Write the filtered topology to disk
    filtered_topology.save(output_structure_file.path)

    # Check the output file exists at this point
    # If not then it means something went wrong with gromacs
    if not output_structure_file.exists:
        raise SystemExit('Something went wrong with PyTraj')


filter_topology.format_sets = [
    {
        'inputs': {
            'input_structure_file': pytraj_supported_structure_formats,
        },
        'outputs': {
            'output_structure_file': pytraj_supported_structure_formats
        }
    }
]

# Given a corrupted NetCDF file, whose first frames may be read by pytraj, find the first corrupted frame number
def find_first_corrupted_frame (input_topology_filepath, input_trajectory_filepath) -> int:
    # Iterload the trajectory to pytraj
    trajectory = get_pytraj_trajectory(input_topology_filepath, input_trajectory_filepath)
    # Iterate frames until we find one frame whose last atom coordinates are all zeros
    frame_iterator = iter(trajectory.iterframe())
    expected_frames = trajectory.n_frames
    for f, frame in enumerate(frame_iterator, 1):
        print(f'Reading frame {f}/{expected_frames}', end='\r')
        # Make sure there are actual coordinates here
        # If there is any problem we may have frames with coordinates full of zeros
        last_atom_coordinates = frame.xyz[-1]
        if not last_atom_coordinates.any():
            return f
    return None
    