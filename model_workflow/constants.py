# CONSTANTS ---------------------------------------------------------------------------

# Database
DEFAULT_API_URL = 'https://mdposit-dev.mddbr.eu/api'

# Selections
# Set a standard selection for protein and nucleic acid backbones in vmd syntax
PROTEIN_AND_NUCLEIC = 'protein or nucleic'
PROTEIN_AND_NUCLEIC_BACKBONE = "(protein and name N CA C) or (nucleic and name P O5' O3' C5' C4' C3')"

# Purely input filenames
DEFAULT_INPUTS_FILENAME = 'inputs.json'
DEFAULT_POPULATIONS_FILENAME = 'populations.json'
DEFAULT_TRANSITIONS_FILENAME = 'transitions.json'

# Input files processing intermediate steps
# We name differenlty every intermediate file and we never rename/overwrite any input or intermediate file
# This allows us to know where we were in case the process was interrupted and not repeat steps on reset
# Intermediate files are removed at the end of the process if it was successful

CONVERTED_STRUCTURE = 'converted.pdb'
CONVERTED_TRAJECTORY = 'converted.xtc'

FILTERED_STRUCTURE = 'filtered.pdb'
FILTERED_TRAJECTORY = 'filtered.xtc'

IMAGED_STRUCTURE = 'imaged.pdb'
IMAGED_TRAJECTORY = 'imaged.xtc'

# Input and output core files
TOPOLOGY_FILENAME = 'topology.json'
STRUCTURE_FILENAME = 'structure.pdb'
TRAJECTORY_FILENAME = 'trajectory.xtc'

# Intermediate filenames
REGISTER_FILENAME = '.register.json'
# Set the input values to be saved in the project register
REGISTER_INPUTS = [
    'directory',
    'accession',
    'database_url',
    'inputs_filepath',
    'input_topology_filepath',
    'input_structure_filepath',
    'input_trajectory_filepaths',
    'populations_filepath',
    'transitions_filepath',
    'md_directories',
    'reference_md_index',
    'filter_selection',
    'pbc_selection',
    'image',
    'fit',
    'translation',
    'mercy',
    'trust',
    'pca_selection',
    'pca_fit_selection',
    'rmsd_cutoff',
    'interaction_cutoff',
    'sample_trajectory',
]

# An old system for when original topology is very wrong and charges must be provided manually
RAW_CHARGES_FILENAME = 'charges.txt'
# Accepted topology formats for atomic charges mining
ACCEPTED_TOPOLOGY_FORMATS = ['top', 'psf', 'prmtop', 'prm7']

# Set generated file names
FIRST_FRAME_FILENAME = 'first_frame.pdb'
AVERAGE_STRUCTURE_FILENAME = 'average.pdb'

# Set output files generated to be uploaded to the database

# Set the output metadata file
OUTPUT_METADATA_FILENAME = 'metadata.json'

# Set the output screenshot filename
OUTPUT_SCREENSHOT_FILENAME = 'mdf.screenshot.jpg'

# Set analyses files to be generated
OUTPUT_INTERACTIONS_FILENAME = 'mda.interactions.json'
OUTPUT_RMSDS_FILENAME = 'mda.rmsds.json'
OUTPUT_TMSCORES_FILENAME = 'mda.tmscores.json'
OUTPUT_RMSF_FILENAME = 'mda.rmsf.json'
OUTPUT_RGYR_FILENAME = 'mda.rgyr.json'
OUTPUT_PCA_FILENAME = 'mda.pca.json'
OUTPUT_PCA_PROJECTION_PREFIX = 'mdt.pca_trajectory'
OUTPUT_PCA_CONTACTS_FILENAME = 'mda.pca_contacts.json'
OUTPUT_RMSD_PERRES_FILENAME = 'mda.rmsd_perres.json'
OUTPUT_RMSD_PAIRWISE_FILENAME = 'mda.rmsd_pairwise.json'
OUTPUT_DIST_PERRES_FILENAME = 'mda.dist_perres.json'
OUTPUT_HBONDS_FILENAME = 'mda.hbonds.json'
OUTPUT_SASA_FILENAME = 'mda.sasa.json'
OUTPUT_ENERGIES_FILENAME = 'mda.energies.json'
OUTPUT_POCKETS_FILENAME = 'mda.pockets.json'
OUTPUT_POCKET_STRUCTURES_PREFIX = 'mdf.pocket' # WARNING: If this is changed then the pockets function must be updated as well
OUTPUT_HELICAL_PARAMETERS_FILENAME = 'mda.helical.json'
OUTPUT_MARKOV_FILENAME = 'mda.markov.json'

# Set folder names for some analyses which generate a lot of intermediate step files
ENERGIES_FOLDER = 'energies'
POCKETS_FOLDER = 'mdpocket'

# Set problematic signs for directory/folder names
FORBIDEN_DIRECTORY_CHARACTERS = ['.', ',', ';', ':']

# Default parameters
DEFAULT_RMSD_CUTOFF = 9
DEFAULT_INTERACTION_CUTOFF = 0.1

# Set the different test flags
STABLE_BONDS_FLAG = 'stabonds'
COHERENT_BONDS_FLAG = 'cohbonds'
TRAJECTORY_INTEGRITY_FLAG = 'intrajrity'
REFERENCE_SEQUENCE_FLAG = 'refseq'
STABLE_INTERACTIONS_FLAG = 'interact'

# State all the available checkings, which may be trusted
AVAILABLE_CHECKINGS = [ STABLE_BONDS_FLAG, COHERENT_BONDS_FLAG, TRAJECTORY_INTEGRITY_FLAG ]
# State all critical process failures, which are to be lethal for the workflow unless mercy is given
AVAILABLE_FAILURES = AVAILABLE_CHECKINGS + [ REFERENCE_SEQUENCE_FLAG, STABLE_INTERACTIONS_FLAG ]

# Terminal colors
# https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal
GREEN_HEADER = '\033[92m'
CYAN_HEADER = '\033[96m'
YELLOW_HEADER = '\033[93m'
RED_HEADER = '\033[91m'
GREY_HEADER = '\033[90m'
COLOR_END = '\033[0m'

# Set a dictionary to parse an internal raw name to a pretty human firendly name
NICE_NAMES = {
    STABLE_BONDS_FLAG: 'Stable bonds test',
    COHERENT_BONDS_FLAG: 'Coherent bonds test',
    TRAJECTORY_INTEGRITY_FLAG: 'Trajectory integrity test',
    REFERENCE_SEQUENCE_FLAG: 'Reference sequence match',
    STABLE_INTERACTIONS_FLAG: 'Interactions are stable'
}