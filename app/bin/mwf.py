#!/usr/bin/env python

from pathlib import Path

import argparse

import pytraj as pt

import index as model_index

from analyses.generic_analyses import rmsd, rmsf, rgyr
from analyses.pca import pca
from analyses.pca_contacts import pca_contacts
from analyses.rmsd_per_residue import rmsd_per_residue
from analyses.rmsd_pairwise import rmsd_pairwise
from analyses.distance_per_residue import distance_per_residue
from analyses.hydrogen_bonds import hydrogen_bonds
from analyses.energies import energies
from analyses.pockets import pockets


def required_length(nmin, nmax):
    """Require minimum and maximum number of values for argument."""
    class RequiredLength(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            if not nmin <= len(values) <= nmax:
                msg = (
                    f"argument \"{self.dest}\" requires between "
                    f"{nmin} and {nmax} arguments")
                raise argparse.ArgumentTypeError(msg)
            setattr(args, self.dest, values)
    return RequiredLength


def execute_workflow(args):
    start_args = {
        "directory": Path(args.working_dir).resolve(),
        "project": args.project,
        "url": args.url,
        "inputs_filename": args.inputs_filename}
    model_index.start(**start_args)

    trajectory_filename = "md.imaged.rot.xtc"
    # trajectory_filename = "md.trr"
    topology_filename = "md.imaged.rot.dry.pdb"
    if not args.single_analysis:
        # run all analyses
        model_index.run_analyses(
            topology_filename, trajectory_filename)
    else:
        # run analysis prep
        metadata, topology_reference, interactions = model_index.analysis_prep(
            inputs_filename=args.inputs_filename)

        pt_trajectory = pt.iterload(
            trajectory_filename,
            topology_filename)[0:2000:10]

        analysis_functions = {
            # "key": [func, args],
            "rmsd": (rmsd, {
                "input_first_frame_filename": "firstFrame.pdb",
                "input_trajectory_filename": trajectory_filename,
                "output_analysis_filename": "md.rmsd.xvg"
            }),
            "rmsf": (rmsf, {
                "input_topology_filename": topology_filename,
                "input_trajectory_filename": trajectory_filename,
                "output_analysis_filename": "md.rmsf.xvg"
            }),
            "rgyr": (rgyr, {
                "input_topology_filename": topology_filename,
                "input_trajectory_filename": trajectory_filename,
                "output_analysis_filename": "md.rgyr.xvg"
            }),
            "pca": (pca, {
                "input_topology_filename": topology_filename,
                "input_trajectory_filename": trajectory_filename,
                "output_eigenvalues_filename": "pca.eigenval.xvg",
                "output_eigenvectors_filename": "eigenvec.trr",
                "snapshots": metadata["SNAPSHOTS"]
            }),
            "pca_contacts": (pca_contacts, {
                "trajectory": trajectory_filename,
                "topology": topology_filename,
                "interactions": interactions,
                "output_analysis_filename": "contacts_PCA.json"
            }),
            "rmsd_per_residue": (rmsd_per_residue, {
                "pt_trajectory": pt_trajectory,
                "output_analysis_filename": "md.rmsd.perres.json",
                "topology_reference": topology_reference
            }),
            "rmsd_pairwise": (rmsd_pairwise, {
                "pt_trajectory": pt_trajectory,
                "output_analysis_filename": "md.rmsd.pairwise.json",
                "interactions": interactions
            }),
            "distance_per_residue": (distance_per_residue, {
                "pt_trajectory": pt_trajectory,
                "output_analysis_filename": "md.dist.perres.json",
                "interactions": interactions
            }),
            "hydrogen_bonds": (hydrogen_bonds, {
                "pt_trajectory": pt_trajectory,
                "output_analysis_filename": "md.hbonds.json",
                "topology_reference": topology_reference,
                "interactions": interactions
            }),
            "energies": (energies, {
                "input_topology_filename": topology_filename,
                "input_trajectory_filename": trajectory_filename,
                "output_analysis_filename": "md.energies.json",
                "reference": topology_reference,
                "snapshots": metadata["SNAPSHOTS"],
                "ligands": metadata["LIGANDS"]
            }),
            "pockets": (pockets, {
                "input_topology_filename": topology_filename,
                "input_trajectory_filename": trajectory_filename,
                "output_analysis_filename": "md.pockets.json",
                "topology_reference": topology_reference,
                "snapshots": metadata["SNAPSHOTS"]
            })
        }

        # execute single analysis function
        print(f"\nExecuting analys function {args.single_analysis}...")
        analysis_func, analysis_args = analysis_functions[args.single_analysis]
        analysis_func(**analysis_args)

    print("\nDone!")


if __name__ == "__main__":
    # define arguments
    parser = argparse.ArgumentParser(description="MoDEL Workflow")

    # optional args
    parser.add_argument(
        "-dir", "--working_dir",
        default=Path.cwd(),
        help="directory where to perform analysis. "
        "If empty, will use current directory.")

    parser.add_argument(
        "-p", "--project",
        default=None,
        help="If given a project name, trajectory and "
        "topology files will be downloaded from remote server.")

    parser.add_argument(
        "-url",
        default="https://bioexcel-cv19-dev.bsc.es",
        help="URL from where to download project")

    parser.add_argument(
        "-in", "--inputs_filename",
        default="inputs.json",
        help="path to inputs filename")

    parser.add_argument(
        "-a", "--single_analysis",
        choices=[
            "rmsd",
            "rmsf",
            "rgyr",
            "pca",
            "pca_contacts",
            "rmsd_per_residue",
            "rmsd_pairwise",
            "distance_per_residue",
            "hydrogen_bonds",
            "energies",
            "pockets"
        ],
        help="Indicate single analysis to perform.")

    args = parser.parse_args()
    execute_workflow(args)
