# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import json

import spack.util.spack_yaml as syaml

import ramble.experimental.uploader
import ramble.cmd
import ramble.reports
from ramble.util.logger import logger

description = "take actions on experiment results"
section = "results"
level = "short"


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest="results_command")

    upload_parser = sp.add_parser(
        "upload", help=results_upload.__doc__, description=results_upload.__doc__
    )
    upload_parser.add_argument("filename", help="path of file to upload")

    report_parser = sp.add_parser(
        "report", help=results_report.__doc__, description=results_report.__doc__
    )
    report_parser.add_argument(
        "--workspace",
        dest="workspace",
        metavar="WRKSPC",
        action="store",
        help="the workspace to report on",
    )

    # The plot type should be exclusive, and only one plot type is supported per invocation
    plot_type_group = report_parser.add_mutually_exclusive_group(required=True)
    plot_type_group.add_argument(
        "--strong-scaling",
        dest="strong_scaling",
        nargs="+",
        help="generate a scaling report, requires two args: [y-axis metric] [x-axis metric]"
        "[optional: group by]",
        required=False,
    )
    plot_type_group.add_argument(
        "--weak-scaling",
        dest="weak_scaling",
        nargs="+",
        help="generate a scaling report, requires two args: [y-axis metric] [x-axis metric]"
        "[optional: group by]",
        required=False,
    )
    plot_type_group.add_argument(
        "--multi-line",
        dest="multi_line",
        nargs="+",
        help="generate a scaling report, requires two args: [y-axis metric] [x-axis metric]"
        "[optional: group by]",
        required=False,
    )
    plot_type_group.add_argument(
        "--compare",
        dest="compare",
        nargs="+",
        help="generate a comparison report, requires at least two args: [FOM 1] [Additional FOMs]"
        "[optional: group by(s)]",
        required=False,
    )
    plot_type_group.add_argument(
        "--foms",
        dest="foms",
        action="store_true",
        help="generate a FOM report, showing values of FOMs for each experiment",
        required=False,
    )
    report_parser.add_argument(
        "--pandas-where",
        dest="where",
        action="store",
        help="Down select data to plot (useful for complex workspaces with collisions). Takes"
        " pandas query format",
        required=False,
    )
    report_parser.add_argument(
        "-n",
        "--normalize",
        dest="normalize",
        action="store_true",
        help=(
            "Normalize charts where possible. For scaling charts, this requires fom_type to be "
            "specified as either 'time' or 'throughput' in the application definition."
        ),
        required=False,
    )
    report_parser.add_argument(
        "--logx", dest="logx", action="store_true", help=("Plot X axis as log"), required=False
    )
    report_parser.add_argument(
        "--logy", dest="logy", action="store_true", help=("Plot Y axis as log"), required=False
    )

    # TODO: should this make it into the final cut? Only applies to multi line -- remove
    report_parser.add_argument(
        "--split-by",
        dest="split_by",
        # nargs="+",
        # action="append",
        # default=["simplified_workload_namespace"],
        action="store",
        default="simplified_workload_namespace",
        help=("Ramble Variable to split out into different plots"),
        required=False,
    )
    report_parser.add_argument("-f", "--file", help="path of results file")


def results_upload(args):
    """Imports Ramble experiment results from JSON file and uploads them as
    specified in the upload block of Ramble's config file."""
    imported_results = import_results_file(args.filename)

    ramble.experimental.uploader.upload_results(imported_results)


def import_results_file(filename):
    """
    Import Ramble experiment results from a JSON or YAML file.

    Returns a results dictionary.
    """
    logger.debug("File to import:")
    logger.debug(filename)

    with open(filename) as imported_file:
        logger.msg(f"Importing results file: {filename}")

        ext = os.path.splitext(filename)[1]
        if ext.lower() == ".json":
            try:
                results_dict = json.load(imported_file)
                # Check if data contains an experiment
                if results_dict.get("experiments"):
                    return results_dict
                else:
                    logger.die("Unable to parse file: Does not contain valid data to import.")
            except ValueError:
                logger.die("Unable to parse file: Invalid JSON formatting.")
        elif ext.lower() in (".yml", ".yaml"):
            try:
                results_dict = syaml.load(imported_file)
                # Check if data contains an experiment
                if results_dict.get("experiments"):
                    return results_dict
                else:
                    logger.die("Unable to parse file: Does not contain valid data to import.")
            except ValueError:
                logger.die("Unable to parse file: Invalid YAML formatting.")
        else:
            logger.die("Unable to parse file: Please provide a valid JSON or YAML results file.")


def results_report(args):
    """Create a report with charts from Ramble experiment results."""
    results_dict = ramble.reports.load_results(args)

    ws_name = results_dict["workspace_name"]
    if not ws_name:
        ws_name = "unknown_workspace"

    if args.workspace:
        ws_name = str(args.workspace)

    results_df = ramble.reports.prepare_data(results_dict, args.where)
    ramble.reports.make_report(results_df, ws_name, args)


def results(parser, args):
    action = {"upload": results_upload, "report": results_report}
    action[args.results_command](args)
