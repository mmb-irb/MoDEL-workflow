# Processing the interactions means finding the residues of each interacting agent
# In addition, interface residues are listed appart

import itertools

from model_workflow.tools.get_reduced_trajectory import get_reduced_trajectory
from model_workflow.utils.auxiliar import InputError, TestFailure, load_json, save_json, warn, reprint
from model_workflow.utils.constants import STABLE_INTERACTIONS_FLAG
from model_workflow.utils.type_hints import *
from model_workflow.utils.vmd_spells import get_covalent_bonds_between, get_interface_atom_indices

# Set the default distance cutoff in Ångstroms (Å)
# This is useful for atomistic simulations
DEFAULT_DISTANCE_CUTOFF = 5

# Set the flag used to label failed interactions
FAILED_INTERACTION_FLAG = 'failed'

# Find interfaces by computing a minimum distance between residues along the trajectory
# Residues are filtered by minimum distance along the trajectory
# The heavy results of interactions are stored in a json file which is uploaded to the database independently
# This file is also used as a backup here, since calculating interactions is a heavy calculation
# In addition, this file may be used to force interactions with custom interface residues manually
def process_interactions (
    input_interactions : Optional[list],
    structure_file : 'File',
    trajectory_file : 'File',
    structure : 'Structure',
    snapshots : int,
    processed_interactions_file : 'File',
    mercy : List[str],
    register : 'Register',
    frames_limit : int,
    interactions_auto : str,
    ligand_map : List[dict],
    pbc_selection : 'Selection',
    # Percent of frames where an interaction must have place (from 0 to 1)
    # If the interactions fails to pass the cutoff then the workflow is killed and the user is warned
    interaction_cutoff : float = 0.1,
    ) -> list:

    print('-> Processing interactions')

    # Copy input interactions to avoid input mutation
    interactions = []
    if type(input_interactions) == list:
        # Duplicate the input interactions to avoid modifying the originals
        interactions = [ { k:v for k,v in interaction.items() } for interaction in input_interactions ]

    # Set the protocol for guessing interactions automatically
    auto = interactions_auto
    # If the protocol is simply "true" then consider the greedy option
    if auto == True: auto = 'greedy'

    # If interactions are to be automatically defined, there are two options
    if auto:
        # We only consider three cases: all chains interactions, only two or all chains vs one
        if not auto == 'greedy' and not auto == 'humble' and not auto == 'ligands' and len(auto[0]) != 1:
            raise InputError('Invalid input auto. Please select "greedy", "humble", "ligands" or the letter of the chain to be used')
        if auto == 'greedy' or auto == 'humble' or auto == 'ligands':
            print(f' |-> Processing interactions automatically. Option "{auto}" is selected')
        else:
            print(f' |-> Processing interactions automatically. Chain "{auto[0]}" is selected')

        # Get structure chains which are not completely in PBC
        target_selection = structure.select_protein()
        target_structure = structure.filter(target_selection)
        target_chains = [ chain for chain in target_structure.chains if chain.get_selection() - pbc_selection ]
        # The greedy option is to find all possible interactions between chains
        if auto == 'autogreedy' or auto == 'greedy':
            # Use itertools to get all possible combinations of chains
            for chain1, chain2 in itertools.combinations(target_chains, 2):
                interaction = {
                    "name": f"chain {chain1.name}-chain {chain2.name} interaction",
                    "agent_1": f"chain {chain1.name}",
                    "agent_2": f"chain {chain2.name}",
                    "selection_1": f"chain {chain1.name}",
                    "selection_2": f"chain {chain2.name}"
                }
                interactions.append(interaction)
            mercy = STABLE_INTERACTIONS_FLAG
            
        # The humble option is to find the interaction between two chains. If there are more than two chains then it won't work
        elif auto == 'autohumble' or auto == 'humble':
            # Make sure there are only 2 chains
            if len(target_chains) != 2: raise InputError('With input "autohumble" there must be exactly 2 chains in the structure. If not, use "autogreedy" or select the interactions manually')
            # If there are exactly two chains then we find the interaction between them
            chain1 = target_chains[0]
            chain2 = target_chains[1]
            interaction = {
                "name": f"chain {chain1.name}-chain {chain2.name} interaction", 
                "agent_1": f"chain {chain1.name}",
                "agent_2": f"chain {chain2.name}", 
                "selection_1": f"chain {chain1.name}",
                "selection_2": f"chain {chain2.name}"
            }
            interactions.append(interaction)
        # If the input is a single letter then it means only one chain is selected so we find the interactions with all other chains
        elif len(auto) == 1:
            # Find the chain selected by the user
            selected_chain = auto
            matching_chain = next((chain for chain in target_chains if selected_chain == chain.name), None)
            # If the chain is not found then raise an error
            if not matching_chain:
                raise InputError(f'Selected chain "{selected_chain}" is not present in the structure')
            for chain in target_chains:
                # Skip interaction of the selected chain with itself
                if chain == selected_chain: continue
                interaction = {
                    "name": f"chain {selected_chain.name}-chain {chain.name} interaction",
                    "agent_1": f"chain {selected_chain.name}",
                    "agent_2": f"chain {chain.name}",
                    "selection_1": f"chain {selected_chain.name}",
                    "selection_2": f"chain {chain.name}"
                }
                interactions.append(interaction)
        
            # In this case, we assume that the user wants to interact the selected chain with all other chains so we force the analysis to be run anyway
            mercy = STABLE_INTERACTIONS_FLAG
        
        elif auto == 'ligands':
            # If there are no ligands present or matched in the structure then we skip ligand interactions
            if not ligand_map:
                raise InputError('No ligand map is detected. Skipping ligand interactions')
            # Iterate over the list of matched ligands in the structure
            for ligand in ligand_map:
                # Get the ligand atom selection
                ligand_selection = structure.select_residue_indices(ligand['residue_indices'])
                # Get ligand fragments
                # AGUS: De esta forma evitamos que si un mismo ligando aparece más de una vez en la simulación (solo habrá un ligand map con el mismo nombre),
                # AGUS: se hagan las interacciones correspondientes con cada uno de estos, es decir, como si fueran ligandos diferentes (cada uno con su respectiva interacción)
                ligand_fragments = structure.find_fragments(ligand_selection)
                for lf, ligand_fragment in enumerate(ligand_fragments, 1):
                    # Match the ligand residue with the chain it belongs to and its classification
                    ligand_residue_indices = structure.get_selection_residue_indices(ligand_fragment)
                    residues = [ structure.residues[index] for index in ligand_residue_indices ]
                    ligand_chains = set([ residue.chain for residue in residues ])
                    # AGUS: la clasificacion del ligando deberia mejorarse para no ser 'Other Chain' sino 'ligand' --> modificar Chain
                    ligand_classifications = set([ chain.classification for chain in ligand_chains ])
                    # Create the ligand interaction with all chains
                    for chain in target_chains:
                        # Skip interaction of the ligand with itself
                        if chain in ligand_chains: continue
                        # Skip interaction if the ligand classifications are the same as the chain classification
                        if chain.classification in ligand_classifications: continue
                        interaction = {
                            "name": f"ligand {ligand['name']} {lf}-chain {chain.name} interaction",
                            "agent_1": f"ligand {ligand['name']} {lf}",
                            "agent_2": f"chain {chain.name}",
                            "selection_1": ligand_fragment.to_vmd(), # AGUS: parcheado por si hubiera más de un residuo por ligando ¿?
                            "selection_2": f"chain {chain.name}"
                        }
                        interactions.append(interaction)
            mercy = STABLE_INTERACTIONS_FLAG

        else:
            raise InputError(f'Invalid input auto interactions "{auto}"')

    # If there are no interactions return an empty list
    interaction_count = len(interactions)
    if not interactions or interaction_count == 0:
        return []
    
    # Make sure there are no interactions with the same name
    interaction_names = [ interaction['name'] for interaction in interactions ]
    if len(set(interaction_names)) < len(interaction_names):
        raise InputError('Interactions must have unique names')
    # Print an empty line for the next reprint
    print()
    # Check input interactions to be correct
    for i, interaction in enumerate(interactions, 1):
        name = interaction["name"]
        reprint(f' Finding interaction type in {name} ({i}/{interaction_count})')
        # Check agents have different names
        if interaction['agent_1'] == interaction['agent_2']:
            raise InputError(f'Interaction agents must have different names at {name}')
        # Check agents have different selections
        if interaction['selection_1'] == interaction['selection_2']:
            raise InputError(f'Interaction agents must have different selections at {name}')
        # Make sure both agents have valid selections
        agent_1_selection = structure.select(interaction['selection_1'])
        if not agent_1_selection:
            raise InputError(f'Interaction "{name}" has a non valid (or empty) selection for agent 1 ({interaction["agent_1"]}): {interaction["selection_1"]}')
        agent_2_selection = structure.select(interaction['selection_2'])
        if not agent_2_selection:
            raise InputError(f'Interaction "{name}" has a non valid (or empty) selection for agent 2 ({interaction["agent_2"]}): {interaction["selection_2"]}')
        # Make sure selections do not overlap at all
        # This makes not sense as interactions are implemented in this workflow
        overlap = agent_1_selection & agent_2_selection
        if overlap:
            raise InputError(f'Agents in interaction "{name}" have {len(overlap)} overlapping atoms')
        # Check if there was a type already assigned to the interaction
        # This is not supported anymore since the interaction type is set automatically
        if 'type' in interaction:
            warn(f'Interaction type "{interaction["type"]}" is set for interaction "{name}".\n'
                 'Interaction type is now calculated and the input interaction type is no longer supported.\n'
                 'Note that the input value will be ignored')
        # Set the interaction type
        # LORE: The type was a user input back in time but now we find it automatically
        # WARNING: Do not calculate the type from the interface residue instead of the whole agent
        # WARNING: This seems more coherent BUT the type will be written in the PROJECT metadata
        # WARNING: Interaction type is a valuable search parameter and thus it must remain in project metadata
        # WARNING: However we could have different types in different MDs, if the interaction is different
        agent_1_classification = structure.get_selection_classification(agent_1_selection)
        agent_2_classification = structure.get_selection_classification(agent_2_selection)
        alphabetically_sorted = sorted([agent_1_classification, agent_2_classification])
        interaction['type'] = f'{alphabetically_sorted[0]}-{alphabetically_sorted[1]}'

    # If there is a backup then use it
    # Load the backup and return its content as it is
    if processed_interactions_file.exists:
        loaded_interactions = load_interactions(processed_interactions_file, structure)
        # Make sure the backup has atom indices
        sample = loaded_interactions[0]
        has_atom_indices = 'atom_indices_1' in sample
        if has_atom_indices:
            # Merge the loaded interactions with the input interactions to cover all fields
            complete_interactions = []
            for input_interaction, loaded_interaction in zip(interactions, loaded_interactions):
                complete_interaction = { **input_interaction, **loaded_interaction }
                complete_interactions.append(complete_interaction)
            return complete_interactions
        # Otherwise it means this is not a compatible version and we must run interactions again
        warn('Interactions backup is obsolete. Interactions will be calculated again')

    # Reset warnings related to this analysis
    register.remove_warnings(STABLE_INTERACTIONS_FLAG)

    # If trajectory frames number is bigger than the limit we create a reduced trajectory
    reduced_trajectory_filepath, step, frames = get_reduced_trajectory(
        structure_file,
        trajectory_file,
        snapshots,
        frames_limit,
    )

    # Get the structure coarse grain selection for further reference
    cg_selection = structure.select_cg()

    # Iterate over each defined interaction
    for interaction in interactions:
        # Set the distance cutoff
        distance_cutoff = interaction.get('distance_cutoff', DEFAULT_DISTANCE_CUTOFF)
        # Find if this interaction has coarse grain atoms involved
        agent_1_selection = structure.select(interaction['selection_1'])
        agent_2_selection = structure.select(interaction['selection_2'])
        has_agent_1_cg = bool(agent_1_selection & cg_selection)
        has_agent_2_cg = bool(agent_2_selection & cg_selection)
        interaction['has_cg'] = has_agent_1_cg or has_agent_2_cg
        # Check if we are using the defualt atomistic distance while selections are coarse grain
        # If this is the case then warn the user
        if interaction['has_cg'] and distance_cutoff == DEFAULT_DISTANCE_CUTOFF:
            warn(f'Using atomistic default distance cutoff ({distance_cutoff}Å) with coarse grain agent(s)\n'
            f'  You may need to manually specify the distance cutoff in the inputs file for interaction "{interaction["name"]}"')
        # Find out the interaction residues for each frame and save all residues as the overall interface
        interface_results = get_interface_atom_indices(
            structure_file.path,
            reduced_trajectory_filepath,
            interaction['selection_1'],
            interaction['selection_2'],
            distance_cutoff
        )
        # Check if the interaction is respecting the frames percent cutoff and if it fails then kill it
        frames_percent = interface_results['interacting_frames'] / interface_results['total_frames']
        pretty_frames_percent = str(round(frames_percent * 100) / 100)
        if frames_percent < interaction_cutoff:
            meaning_log = 'is not happening at all' if frames_percent == 0 else 'is happening only in a small percent of the trajectory'
            print(f'Interaction "{interaction["name"]}" is not reaching the frames percent cutoff of {interaction_cutoff} ({pretty_frames_percent}).\n'
                f'This means the interaction {meaning_log}.\n'
                'Check agent selections are correct or consider removing this interaction from the inputs.\n'
                f'   - Agent 1 selection: {interaction["selection_1"]}\n'
                f'   - Agent 2 selection: {interaction["selection_2"]}')
            # Check if we must have mercy in case of interaction failure
            must_be_killed = STABLE_INTERACTIONS_FLAG not in mercy
            if must_be_killed:
                raise TestFailure('An interaction failed to be set.\n'
                    'Use the "--mercy interact" flag for the workflow to continue.\n'
                    'Failed interactions will be removed from further analyses.')
            # If the workflow is not to be killed then just remove this interaction from the interactions list
            # Thus it will not be considered in interaction analyses and it will not appear in the metadata
            interaction[FAILED_INTERACTION_FLAG] = True
             # If this is an automated process then there is no need to warn the user
            if auto: continue
            register.add_warning(STABLE_INTERACTIONS_FLAG, 'Some interaction(s) are not stable enough so their analyses are skipped')
            continue
        # For each agent in the interaction, get the residues in the interface from the previously calculated atom indices
        for agent in ['1','2']:
            # First with all atoms/residues
            atom_indices = interface_results[f'selection_{agent}_atom_indices']
            residue_indices = sorted(list(set([ structure.atoms[atom_index].residue_index for atom_index in atom_indices ])))
            # Check residue lists to not be empty, which should never happen
            if len(residue_indices) == 0:
                agent_name = interaction['agent_' + agent]
                raise ValueError(f'Empty selection for agent "{agent_name}" in interaction "{interaction["name"]}": {interaction["selection_" + agent]}')
            interaction[f'residue_indices_{agent}'] = residue_indices
            interaction[f'residues_{agent}'] = [ structure.residues[residue_index] for residue_index in residue_indices ]
            # Then with interface atoms/residues
            interface_atom_indices = interface_results[f'selection_{agent}_interface_atom_indices']
            interface_residue_indices = sorted(list(set([ structure.atoms[atom_index].residue_index for atom_index in interface_atom_indices ])))
            interaction[f'interface_indices_{agent}'] = interface_residue_indices
            interaction[f'interface_{agent}'] = [ structure.residues[residue_index] for residue_index in interface_residue_indices ]
            # Save atom indices in the interaction object
            interaction[f'atom_indices_{agent}'] = atom_indices
            interaction[f'interface_atom_indices_{agent}'] = interface_atom_indices
            interaction['version'] = '1.0.0'

        # Find strong bonds between residues in different interfaces
        # Use the main topology, which is corrected and thus will retrieve the right bonds
        strong_bonds = get_covalent_bonds_between(structure_file.path, interaction['selection_1'], interaction['selection_2'])

        # Translate all residues selections to pytraj notation
        # These values are used along the workflow but not added to metadata
        converter = structure.residue_2_pytraj_residue_index
        interaction.update(
            {
                'pt_residues_1': list(map(converter, interaction['residues_1'])),
                'pt_residues_2': list(map(converter, interaction['residues_2'])),
                'pt_interface_1': list(map(converter, interaction['interface_1'])),
                'pt_interface_2': list(map(converter, interaction['interface_2'])),
                'strong_bonds': strong_bonds
            }
        )

        print(f'{interaction["name"]} ({pretty_frames_percent}) (type: {interaction["type"]}) -> {sorted(interaction["interface_indices_1"] + interaction["interface_indices_2"])}')

    # Write the interactions file with the fields to be uploaded to the database only
    # i.e. not vmd selections
    file_keys = [
        'name',
        'agent_1',
        'agent_2',
        'residue_indices_1',
        'residue_indices_2',
        'interface_indices_1',
        'interface_indices_2',
        'atom_indices_1',
        'atom_indices_2',
        'interface_atom_indices_1',
        'interface_atom_indices_2',
        'version',
        'strong_bonds',
        'has_cg',
        FAILED_INTERACTION_FLAG
    ]

    # If automatic interactions are being processed then we must remove failed interactions (this is necessary for futher analyses)
    # AGUS: en principio esto es temporal 
    if auto:
        interactions = [ interaction for interaction in interactions if not interaction.get(FAILED_INTERACTION_FLAG, False) ]
    
    file_interactions = []
    for interaction in interactions:
        file_interaction = { key: value for key, value in interaction.items() if key in file_keys }
        file_interactions.append(file_interaction)

    # Save the interactions file unless all interactions failed
    any_valid_interactions = any( (not interaction.get(FAILED_INTERACTION_FLAG, False)) for interaction in interactions )
    if any_valid_interactions:
        save_json(file_interactions, processed_interactions_file.path, indent = 4)
    return interactions

# Load interactions from an already existing interactions file
def load_interactions (processed_interactions_file : 'File', structure : 'Structure') -> list:
    print(f' Using already calculated interactions in {processed_interactions_file.path}')
    # The stored interactions should carry only residue indices and strong bonds
    interactions = load_json(processed_interactions_file.path)
    # Now we must complete every interactions dict by adding residues in source format and pytraj format
    for interaction in interactions:
        # If the interaction failed then there will be minimal information
        if interaction.get(FAILED_INTERACTION_FLAG, False):
            continue
        # Get residues from their indices
        residues = structure.residues
        interaction['residues_1'] = [ residues[index] for index in interaction['residue_indices_1'] ]
        interaction['residues_2'] = [ residues[index] for index in interaction['residue_indices_2'] ]
        # Check residue lists to not be empty, which should never happen
        if len(interaction['residues_1']) == 0:
            raise ValueError(f'Empty selection for agent "{interaction["agent_1"]}" in interaction "{interaction["name"]}"')
        if len(interaction['residues_2']) == 0:
            raise ValueError(f'Empty selection for agent "{interaction["agent_2"]}" in interaction "{interaction["name"]}"')
        interaction['interface_1'] = [ residues[index] for index in interaction['interface_indices_1'] ]
        interaction['interface_2'] = [ residues[index] for index in interaction['interface_indices_2'] ]
        # Transform to pytraj
        converter = structure.residue_2_pytraj_residue_index
        interaction['pt_residues_1'] = list(map(converter, interaction['residues_1']))
        interaction['pt_residues_2'] = list(map(converter, interaction['residues_2']))
        interaction['pt_interface_1'] = list(map(converter, interaction['interface_1']))
        interaction['pt_interface_2'] = list(map(converter, interaction['interface_2']))
    return interactions