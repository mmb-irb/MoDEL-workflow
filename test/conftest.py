import os
import pytest
import tempfile
from pathlib import Path

from model_workflow.utils.remote import Remote
from model_workflow.utils.file import File
from model_workflow.utils.structures import Structure, Selection
from model_workflow.utils.auxiliar import load_json

# Constants
DATABASE_URL = "https://irb-dev.mddbr.eu/api/"
TEST_ACCESSION = "A01M9.1"
TEST_DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a persistent directory for test data that remains across test runs"""
    # Create a project-specific test data directory
    test_data_dir = os.path.join(TEST_DATA_ROOT, TEST_ACCESSION)
    # Create the directory if it doesn't exist
    os.makedirs(test_data_dir, exist_ok=True)
    return test_data_dir

@pytest.fixture(scope="session")
def remote_client(test_data_dir):
    """Create a Remote client for the test accession"""
    return Remote(database_url=DATABASE_URL, accession=TEST_ACCESSION)

@pytest.fixture(scope="session")
def structure_file(remote_client, test_data_dir):
    """Download and provide the standard structure file"""
    output_path = os.path.join(test_data_dir, f"{TEST_ACCESSION}_structure.pdb")
    file_obj = File(output_path)
    
    # Only download if file doesn't exist yet
    if not file_obj.exists:
        remote_client.download_standard_structure(file_obj)
    
    return file_obj


@pytest.fixture(scope="session")
def structure(structure_file):
    """Load the structure into a Structure object"""
    return Structure.from_pdb_file(structure_file.path)


@pytest.fixture(scope="session")
def topology_file(remote_client, test_data_dir):
    """Download and provide the standard topology file"""
    output_path = os.path.join(test_data_dir, f"{TEST_ACCESSION}_topology.top")
    file_obj = File(output_path)
    
    # Only download if file doesn't exist yet
    if not file_obj.exists:
        remote_client.download_standard_topology(file_obj)
    
    return file_obj

@pytest.fixture(scope="session")
def trajectory_file(remote_client, test_data_dir):
    """Download and provide a trajectory file with a limited frame selection for testing"""
    # For testing, we only need a small subset of frames
    output_path = os.path.join(test_data_dir, f"{TEST_ACCESSION}_trajectory.xtc")
    file_obj = File(output_path)
    
    # Only download if file doesn't exist yet
    if not file_obj.exists:
        # Download only 10 frames for faster testing
        remote_client.download_trajectory(
            file_obj,
            # frame_selection="1:10:1",  # First 10 frames
            format="xtc"
        )
    
    return file_obj

@pytest.fixture(scope="session")
def analysis_file(remote_client, test_data_dir, analysis_type):
    """Download and provide the standard structure file"""
    output_path = os.path.join(test_data_dir, f"{TEST_ACCESSION}_{analysis_type}.json")
    file_obj = File(output_path)
    
    # Only download if file doesn't exist yet
    if not file_obj.exists:
        remote_client.download_analysis_data(analysis_type,  file_obj)
    
    return file_obj

@pytest.fixture(scope="session")
def membrane_map(remote_client, test_data_dir):
    """Download and provide the standard structure file"""
    output_path = os.path.join(test_data_dir, f"{TEST_ACCESSION}_mem-map.json")
    file_obj = File(output_path)
    
    # Only download if file doesn't exist yet
    if not file_obj.exists:
        remote_client.download_analysis_data('mem-map',  file_obj)
    file_obj = load_json(file_obj.path)
    return file_obj

