# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
import datetime
import os
import re

import pandas as pd

# import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import llnl.util.filesystem as fs

import ramble.cmd.results
import ramble.cmd.workspace
import ramble.config
import ramble.filters
from ramble.language.shared_language import BetterDirection
import ramble.pipeline
import ramble.util.path
from ramble.util.logger import logger


def to_numeric_if_possible(series):
    """Try to convert a Pandas series to numeric, or return the series unchanged."""
    try:
        return pd.to_numeric(series)
    except (ValueError, TypeError):
        return series


def load_results(args):
    """Loads results from a file or workspace to use for reports.

    Check for results in this order:
        1. via ``ramble results report -f FILENAME``
        2. via ``ramble -w WRKSPC`` or ``ramble -D DIR`` or
        ``ramble results report --workspace WRKSPC``(arguments)
        3. via a path in the ramble.workspace.ramble_workspace_var environment variable.
    """
    results_dict = {}

    if args.file:
        # FIXME: why does this call back into cmd?
        if os.path.exists(args.file):
            results_dict = ramble.cmd.results.import_results_file(args.file)
        else:
            logger.die(f"Cannot find file {args.file}")
    else:
        ramble_ws = ramble.cmd.find_workspace_path(args)

        if not ramble_ws:
            logger.die(
                "ramble results report requires either a results filename, "
                "a command line workspace, or an active workspace"
            )

        logger.debug("Looking for workspace results file...")
        json_results_path = os.path.join(ramble_ws, "results.latest.json")
        yaml_results_path = os.path.join(ramble_ws, "results.latest.yaml")
        if os.path.exists(json_results_path):
            logger.debug(f"Importing {json_results_path}")
            results_dict = ramble.cmd.results.import_results_file(json_results_path)
        elif os.path.exists(yaml_results_path):
            logger.debug(f"Importing {yaml_results_path}")
            results_dict = ramble.cmd.results.import_results_file(yaml_results_path)
        else:
            logger.die(
                "No JSON or YAML results file was found. Please run "
                "'ramble workspace analyze -f json'."
            )
    return results_dict


def is_repeat_child(experiment):
    try:
        if int(experiment["RAMBLE_VARIABLES"]["repeat_index"]) > 0:
            return True
        else:
            return False
    except:
        # TODO: Remove this old implemention. I keep it here since the JSON update was so recent
        ends_in_number = re.search(r"\.\d+$", experiment["name"])
        if ends_in_number:
            return True
        else:
            return False


def prepare_data(results: dict, where_query) -> pd.DataFrame:
    """Creates a Pandas DataFrame from the results dictionary to use for reports.

    Transforms nested results dictionary into a flat dataframe. Each row equals
    one FOM from one context of one experiment, with columns including
    associated experiment variables (except paths and commands).

    Input (dict):
        {
            "experiments": [
                {"name": "exp_1",
                 "n_nodes": 1,
                 "CONTEXTS": [
                    {"name": "null",
                     "foms": [
                        {"name": "fom_1", "value": 42.0},
                        {"name": "fom_2", "value": 35},
                     ]
                    },
                 ]
                },
                {"name": "exp_2",
                 "n_nodes": 2,
                 "CONTEXTS": [
                    {"name": "null",
                     "foms": [
                        {"name": "fom_1", "value": 56.5},
                        {"name": "fom_2", "value": 73},
                     ]
                    },
                 ]
                },
            ]
        }

    Output (pd.DataFrame):
             name   fom_name    fom_value  n_nodes
        0   exp_1      fom_1         42.0        1
        1   exp_1      fom_2           35        1
        2   exp_2      fom_1         56.5        2
        3   exp_2      fom_2           73        2
    """

    # TODO: is this sufficient?
    # panda = pd.json_normalize(results['experiments'])
    # print(panda['CONTEXTS']) # would need to flatten contexts too
    # Then remove things we don't need, like failures and repeats

    unnest_context = []
    skip_exps = []
    # first unnest dictionaries
    for exp in results["experiments"]:
        # TODO: this does not work as expected for repeats since success is not clear
        # TODO: how to handle success? Repeats make this tricky because some children might have status=success but parent might have status=failed
        # if exp['RAMBLE_STATUS'] != 'SUCCESS' or exp['name'] in skip_exps:

        # TODO: disable skip_exps in favor of a more explicit is_child or is_parent check
        if exp["name"] in skip_exps or is_repeat_child(exp):
            logger.debug(f"Skipping import of experiment {exp['name']}")
            continue
        # FIXME: is this wise? We need to flesh out the CUJ around success/fail
        elif exp["RAMBLE_STATUS"] != "SUCCESS":
            continue
        else:
            logger.debug(f"Importing experiment {exp['name']}")
            # For repeat experiments, use summary stats from base exp and skip repeats
            # Repeats are sequenced after base exp

            if exp.get("N_REPEATS", 0) > 0:
                # Generate repeat experiment names in order to skip them explicitly
                exp_name = exp["name"]
                for n in range(1, exp["N_REPEATS"] + 1):
                    if ".chain" in exp_name:
                        insert_idx = exp_name.index(".chain")
                        repeat_exp_name = exp_name[:insert_idx] + f".{n}" + exp_name[insert_idx:]
                        skip_exps.append(repeat_exp_name)
                    else:
                        skip_exps.append(exp_name + f".{n}")

            for context in exp["CONTEXTS"]:
                for fom in context["foms"]:
                    # Expand to one row per FOM per context w/ a copy of the experiment vars and metadata
                    exp_copy = copy.deepcopy(exp)

                    # Remove context dict and add the current FOM values
                    # TODO: Can we clean this partial copy with a class?
                    exp_copy.pop("CONTEXTS")
                    exp_copy["context"] = context["name"]
                    exp_copy["fom_name"] = fom["name"]
                    exp_copy["fom_value"] = fom["value"]
                    exp_copy["fom_units"] = fom["units"]
                    exp_copy["fom_origin"] = fom["origin"]
                    exp_copy["fom_origin_type"] = fom["origin_type"]

                    if "fom_type" in fom.keys():
                        exp_copy["better_direction"] = fom["fom_type"]["better_direction"]
                    else:  # if using older data file without fom_type
                        exp_copy["better_direction"] = BetterDirection.INDETERMINATE

                    # Flatten final vars dict and drop raw vars dict
                    ##for key in ["RAMBLE_VARIABLES", "RAMBLE_RAW_VARIABLES"]:
                    # if key in exp_copy:
                    # exp_copy.pop(key)

                    # Exclude vars that aren't needed for analysis, mainly paths and commands
                    dir_regex = r"_dir$"
                    path_regex = r"_path$"
                    vars_to_ignore = [
                        "batch_submit",
                        "log_file",
                        "command",
                        "execute_experiment",
                    ]
                    for key, value in exp["RAMBLE_VARIABLES"].items():
                        if key in vars_to_ignore:
                            continue
                        if re.search(dir_regex, key):
                            continue
                        if re.search(path_regex, key):
                            continue
                        exp_copy[key] = value

                    for key, value in exp["RAMBLE_RAW_VARIABLES"].items():
                        if key in vars_to_ignore:
                            continue
                        if re.search(dir_regex, key):
                            continue
                        if re.search(path_regex, key):
                            continue
                        exp_copy["RAW" + key] = value

                    unnest_context.append(exp_copy)

    results_df = pd.DataFrame.from_dict(unnest_context)

    # Apply where to down select
    if where_query:
        logger.info(f"Applying where query: {where_query}")
        results_df = results_df.query(where_query)

    return results_df


class PlotFactory:
    def create_plot_generators(self, args, report_dir_path, pdf_report, results_df):
        plots = []
        normalize = args.normalize
        logx = args.logx
        logy = args.logy
        split_by = args.split_by

        plot_types = [
            (args.strong_scaling, StrongScalingPlot),
            (args.weak_scaling, WeakScalingPlot),
            (args.compare, ComparisonPlot),
            (args.foms, FomPlot),
            (args.multi_line, MultiLinePlot),
        ]

        for specs, plot_class in plot_types:
            if specs:
                if isinstance(specs, bool):
                    specs = [specs]
                for spec in specs:
                    plots.append(
                        plot_class(
                            spec,
                            normalize,
                            report_dir_path,
                            pdf_report,
                            results_df,
                            logx,
                            logy,
                            split_by,
                        )
                    )

        if not plots:
            # TODO: should this be checked in cmd?
            # TODO: make this error more descriptive
            logger.die("No plots requested. Please specify required plots or see help (-h)")
        else:
            return plots


class PlotGenerator:
    def __init__(
        self, spec, normalize, report_dir_path, pdf_report, results_df, logx, logy, split_by
    ):
        self.normalize = normalize
        self.spec = spec
        self.report_dir_path = report_dir_path
        self.pdf_report = pdf_report
        self.figsize = [12, 8]

        self.results_df = results_df
        self.output_df = pd.DataFrame()

        self.logx = logx
        self.logy = logy

        self.split_by = split_by

        # TODO: enable more robustly
        self.have_statistics = False
        self.better_direction = BetterDirection.INDETERMINATE

    def normalize_data(
        self, data, scale_to_index=False, to_col="normalized_fom_value", from_col="fom_value", speedup=False
    ):
        # FIXME: do we need to support more than normalizing by the first
        # value?
        if data[from_col].iloc[0] == 0:
            raise ArithmeticError(
                "Unable to normalize data. The first value in the series cannot be zero."
            )
        else:
            # Adjusts y-value to match scale var if provided (e.g., speedup for 2 nodes = 2)
            if scale_to_index:
                # Performs inplace edit on data, no need to return
                if speedup:
                    data.loc[:, to_col] = (data[from_col].iloc[0] / data.loc[:, from_col]) * data.index[0]
                else:
                    data.loc[:, to_col] = (data.loc[:, from_col] / data[from_col].iloc[0]) * data.index[0]
            else:
                if speedup:
                    data.loc[:, to_col] = data[from_col].iloc[0] / data.loc[:, from_col]
                else:
                    data.loc[:, to_col] = data.loc[:, from_col] / data[from_col].iloc[0]
    # TODO: these args come from the spec, so don't need to be passed and could be stored at init
    def draw(self, perf_measure, scale_var, series, y_label):
        series_data = self.output_df.query(f'series == "{series}"').copy()

        # TODO: add suffix 'higher/lower is better' to chart title based on better_direction
        title = f"{perf_measure} vs {scale_var} for {series}{self.better_direction.get_direction_str()}"
        logger.debug(f"Generating plot for {title}")

        # TODO: prep_draw method in subclass ScalingPlotGenerator, not this class
        fig, ax = self.prep_draw(perf_measure, scale_var)

        if self.normalize:
            ax.plot(
                series_data.index,
                "normalized_fom_value",
                data=series_data,
                marker="o",
                label=f"{perf_measure} (Normalized)",
            )
        else:
            ax.plot(
                series_data.index,
                "fom_value",
                data=series_data,
                marker="o",
                label=f"{perf_measure}",
            )
        ymin, ymax = ax.get_ylim()

        # TODO: the plot can get very compressed for log weak scaling plots
        if not self.logy:
            plt.ylim(0, ymax * 1.1)

        if self.have_statistics:
            logger.debug("Adding fill lines for min and max")
            ax.fill_between(
                series_data.index, "fom_value_min", "fom_value_max", data=series_data, alpha=0.2
            )

        try:
            ax.plot(
                series_data.index, "ideal_perf_value", data=series_data, label="Ideal Value"
            )
        except ValueError:
            logger.debug("Failed to plot ideal_perf_value. Series not found.")

        plt.legend(loc="upper left")

        ax.set_xticks(series_data.index.unique().tolist())
        ax.set_title(title, wrap=True)
        ax.set_ylabel(y_label)
        ax.set_xlabel(scale_var)

        # Rotate to prevent long x-axis labels overlapping. There's probably a better way
        if series_data.index.astype(str).str.len().max() > 4:
            ax.tick_params(axis="x", labelrotation=45)
            fig.tight_layout()

        chart_filename = f"strong-scaling_{perf_measure}_vs_{scale_var}_{series}.png"
        self.write(fig, chart_filename)

    def draw_filler(self, perf_measure, scale_var, series, exception):
        """Draws a filler figure in cases where a chart cannot be drawn due to errors."""
        title = f"{perf_measure} vs {scale_var} for {series}"
        logger.debug(f"Generating filler figure for {title}")

        fig, ax = plt.subplots(figsize=self.figsize)
        fig.text(
            0.5,
            0.5,
            exception,
            horizontalalignment="center",
            verticalalignment="center",
            transform=fig.gca().transAxes,
            fontsize=12,
        )
        ax.set_axis_off()
        ax.set_title(title)

        chart_filename = f"strong-scaling_{perf_measure}_vs_{scale_var}_{series}.png"
        self.write(fig, chart_filename)

    def validate_spec(self, chart_spec):
        """Validates that the FOMs and variables in the chart spec are in the results data."""
        for var in chart_spec:
            if (
                var not in self.results_df.columns
                and var not in self.results_df.loc[:, "fom_name"].values
            ):
                logger.debug(f"Available options: {self.results_df.loc[:, 'fom_name'].unique()}")
                logger.die(f"{var} was not found in the results data.")

    def write(self, fig, filename):
        filename = filename.replace(" ", "-")
        plt.savefig(os.path.join(self.report_dir_path, filename))
        self.pdf_report.savefig(fig)
        plt.close(fig)


class ScalingPlotGenerator(PlotGenerator):
    def generate_plot_data(self):
        """Creates a dataframe for plotting line charts with scaling var on x axis,
        and performance variable on y axis."""
        self.validate_spec(self.spec)

        perf_measure, scale_var, *additional_vars = self.spec

        # FOMs are by row, so select only rows with the perf_measure FOM
        results = self.results_df.query(f'fom_name == "{perf_measure}"').copy()

        # Determine which direction is 'better', or 'INDETERMINATE' if missing or ambiguous data
        if len(results.loc[:, "better_direction"].unique()) == 1:
            self.better_direction = results.loc[:, "better_direction"].unique()[0]

        # TODO: this needs to support a list for split_by
        # TODO: this currently gets overwritten by series, below
        results.loc[:, "series"] = results.loc[:, self.split_by]

        if additional_vars:
            # TODO: this would be nicer as a group by
            results.loc[:, "series"] = (
                results.loc[:, "series"]
                + "_x_"
                + results[additional_vars].agg("_x_".join, axis=1)
            )

        for series in results.loc[:, "series"].unique():

            # TODO: this needs to account for repeats in a more elegant way
            series_results = results.query(
                f'series == "{series}" and (fom_origin_type == "application" '
                'or fom_origin_type == "modifier" or fom_origin_type == "summary::mean")'
            ).copy()

            series_results.loc[:, "fom_value"] = to_numeric_if_possible(
                series_results["fom_value"]
            )
            series_results.loc[:, scale_var] = to_numeric_if_possible(
                series_results[scale_var]
            )
            series_results = series_results.set_index(scale_var)

            self.validate_data(series_results)

            if series_results.loc[:, "fom_origin_type"].iloc[0] == "summary::mean":
                self.have_statistics = True

                # series_results.loc[:, "fom_min"] = results.query(
                series_min = results.query(
                    f'series == "{series}" and fom_origin_type == "summary::min"'
                ).copy()
                series_max = results.query(
                # series_results.loc[:, "fom_max"] = results.query(
                    f'series == "{series}" and fom_origin_type == "summary::max"'
                ).copy()

            # TODO: We interpret this as requesting speedup, which isn't strictly true
            # We need a more clear semantic for this
            if self.normalize:
                try:
                    self.normalize_data(series_results, scale_to_index=True)
                except ArithmeticError as e:
                    logger.warn(e)
                    self.draw_filler(perf_measure, scale_var, series, e)
                    continue

            if self.have_statistics:
                # TODO: fix copy semantics
                # "A value is trying to be set on a copy of a slice from a DataFrame."
                # there might be some accidentally copy semantics with series_results
                series_min.loc[:, scale_var] = to_numeric_if_possible(
                    series_min[scale_var]
                )
                series_min = series_min.set_index(scale_var)
                series_max.loc[:, scale_var] = to_numeric_if_possible(
                    series_max[scale_var]
                )
                series_max = series_max.set_index(scale_var)

                series_results.loc[:, "fom_value_min"] = to_numeric_if_possible(series_min["fom_value"])
                series_results.loc[:, "fom_value_max"] = to_numeric_if_possible(series_max["fom_value"])

                # minmax = pd.DataFrame()
                # minmax["fom_value_min"] = series_min["fom_value"]
                # minmax["fom_value_max"] = series_max["fom_value"]
                # minmax.index = to_numeric_if_possible(series_min.index)

                if self.normalize:
                    self.normalize_data(
                        series_results, scale_to_index=True, to_col="fom_value_min", from_col="fom_value_min", speedup=True
                    )
                    self.normalize_data(
                        series_results, scale_to_index=True, to_col="fom_value_max", from_col="fom_value_max", speedup=True
                    )


                # self.minmax = minmax

            series_results = self.add_idealized_data(results, series_results)
            self.output_df = pd.concat([self.output_df, series_results])

            self.draw(perf_measure, scale_var, series)

    def add_idealized_data(self, raw_results, selected_data):

        if self.normalize:
            first_perf_value = selected_data["normalized_fom_value"].iloc[0]
        else:
            first_perf_value = selected_data["fom_value"].iloc[0]

        if first_perf_value == 0:
            logger.warn(
                "Unable to calculate idealized data. The first value in the series cannot be zero."
            )
            return selected_data

        logger.debug(f"Normalizing data (by {first_perf_value})")

        selected_data.loc[:, "ideal_perf_value"] = first_perf_value

        if self.better_direction == "LOWER" or self.better_direction == BetterDirection.LOWER:
            selected_data["ideal_perf_value"] = selected_data.loc[:, "ideal_perf_value"] / (
                selected_data.index / selected_data.index[0]  # set baseline scaling var to 1
            )
        elif self.better_direction == "HIGHER" or self.better_direction == BetterDirection.HIGHER:
            selected_data["ideal_perf_value"] = selected_data.loc[:, "ideal_perf_value"] * (
                selected_data.index / selected_data.index[0]
            )

        return selected_data


    def validate_spec(self, chart_spec):
        super().validate_spec(chart_spec)
        for chart_spec in self.spec:
            if len(chart_spec) < 2:
                logger.die(
                    "Scaling plot requires two arguments: " "performance metric and scaling metric"
                )

    def validate_data(self, data):
        has_duplicate_index = any(data.index.duplicated())
        if has_duplicate_index:
            logger.debug(data)
            logger.die(f"Attempting to plot none-unique data. Please reduce data and try again")

    def default_better(self):
        return BetterDirection.INDETERMINATE

    def prep_draw(self, perf_measure, scale_var):
        fig, ax = plt.subplots(figsize=self.figsize)

        if self.logx or self.logy:
            from matplotlib.ticker import ScalarFormatter

            formatter = ScalarFormatter()
            formatter.set_scientific(False)

        if self.logx:
            ax.set_xscale("log", base=2)
            ax.xaxis.set_major_formatter(formatter)

        if self.logy:
            ax.set_yscale("log", base=2)
            ax.yaxis.set_major_formatter(formatter)

        return fig, ax


class WeakScalingPlot(ScalingPlotGenerator):
    def draw(self, perf_measure, scale_var, series):
        if self.normalize:
            y_label = "Efficiency"
        else:
            y_label = perf_measure

        super().draw(perf_measure, scale_var, series, y_label)

    def add_idealized_data(
        self, raw_results, selected_data):
        selected_data = super().add_idealized_data(raw_results, selected_data)

        selected_data.loc[:, "ideal_perf_value"] = selected_data["ideal_perf_value"].iloc[0]
        return selected_data


class StrongScalingPlot(ScalingPlotGenerator):
    def default_better(self):
        if self.normalize:
            return BetterDirection.HIGHER
        else:
            return BetterDirection.LOWER

    def add_idealized_data(
        self, raw_results, selected_data):
        # TODO: we need to set the better direction to be the opposite when normalized
        if self.better_direction is BetterDirection.INDETERMINATE:
            self.better_direction = self.default_better()

        return super().add_idealized_data(raw_results, selected_data)

    def normalize_data(
        self, data, scale_to_index=True, to_col="normalized_fom_value", from_col="fom_value", speedup=True
    ):
        super().normalize_data(data, scale_to_index, to_col=to_col, from_col=from_col, speedup=speedup)

    def draw(self, perf_measure, scale_var, series):
        if self.normalize:
            y_label = "Speedup"
        else:
            y_label = perf_measure

        super().draw(perf_measure, scale_var, series, y_label)


class FomPlot(PlotGenerator):
    def generate_plot_data(self):
        # super().generate_plot_data()
        # TODO: what is this for?
        # this one doesn't have a chart spec, it's just a flag
        # first divide results into series based on workload namespace
        # then iterate over each fom in each series and create 1 bar chart per fom
        # comparing fom_value (y) by experiment (x)
        results = self.results_df
        all_foms = results.loc[:, "fom_name"].unique()
        for fom in all_foms:
            series_results = results.query(
                f'fom_name == "{fom}" and (fom_origin_type == "application" or fom_origin_type == "modifier" or fom_origin_type == "summary::mean")'
            ).copy()

            scale_var = "simplified_experiment_namespace"

            # TODO: dry with ScalingPlot code
            series_results.loc[:, "fom_value"] = to_numeric_if_possible(
                series_results["fom_value"]
            )
            series_results.loc[:, scale_var] = to_numeric_if_possible(series_results[scale_var])

            series_results = series_results.set_index(scale_var)
            print("post index")
            print(series_results)

            # self.validate_data(series_results)

            series_min = results.query(
                f'fom_name == "{fom}" and fom_origin_type == "summary::min"'
            )
            series_max = results.query(
                f'fom_name == "{fom}" and fom_origin_type == "summary::max"'
            )
            if self.normalize:
                self.normalize_data(series_results, scale_to_index=True)
                print(series_results)

            if not series_min.empty:
                self.have_statistics = True

                # TODO: fix copy semantics
                # "A value is trying to be set on a copy of a slice from a DataFrame."
                # there might be some accidentally copy semantics with series_results
                series_min = series_min.set_index(scale_var)
                series_max = series_max.set_index(scale_var)

                minmax = pd.DataFrame()
                minmax["fom_value_min"] = series_min["fom_value"]
                minmax["fom_value_max"] = series_max["fom_value"]
                minmax.index = to_numeric_if_possible(series_min.index)

                if self.normalize:
                    self.normalize_data(
                        minmax, scale_to_index=True, to_col="fom_value_min", from_col="fom_value_min", speedup=True
                    )
                    self.normalize_data(
                        minmax, scale_to_index=True, to_col="fom_value_max", from_col="fom_value_max", speedup=True
                    )

                self.minmax = minmax

            self.output_df = series_results

            # TODO: there is probably a more efficient way to get this
            unit = series_results.loc[:, "fom_units"].unique()

            perf_measure = fom
            # scale_var = ""
            series = "experiment_name"
            self.draw(perf_measure, scale_var, series)  # , y_label=unit)

    # TODO: dry bar plot drawing
    def draw(self, perf_measure, scale_var, series):
        # TODO: this will also turn ints to floats, which is not ideal
        try:
            self.output_df["fom_value"] = self.output_df["fom_value"].astype(float)
        except ValueError as e:
            logger.warn(f"Skipping drawing of non numeric FOM: {perf_measure}")
            return

        # TODO: this should leverage the available min/max to add candle sticks
        ax = self.output_df.plot(y="fom_value", kind="bar")
        fig = ax.get_figure()

        # FIXME: this has a hard time fitting well on screen
        # plt.tight_layout()
        # plt.autoscale()
        # ax.set_label('Label via method')
        ax.legend([perf_measure])

        # If all FOMs are either higher or lower is better, add it to chart title
        ax.set_title(f"{perf_measure} by experiment", wrap=True)

        chart_filename = f"foms_{perf_measure}_by_experiments.png"
        self.write(fig, chart_filename)


class ComparisonPlot(PlotGenerator):
    def draw(self, perf_measure, scale_var, series):
        ax = self.output_df.plot(kind="bar")
        fig = ax.get_figure()

        # FIXME: this has a hard time fitting well on screen
        # plt.tight_layout()
        plt.autoscale()

        # If all FOMs are either higher or lower is better, add it to chart title
        title_suffix = ""
        ax.set_title(
            f'{" vs ".join(perf_measure)} by {" and ".join(series)} {title_suffix}', wrap=True
        )

        chart_filename = f'{"_vs_".join(perf_measure)}_by_{"_and_".join(series)}.png'
        self.write(fig, chart_filename)

    def generate_plot_data(self):
        # super().generate_plot_data()

        # Break out input args into FOMs and dimensions
        foms = []
        dimensions = []

        for input_spec in self.spec:
            if input_spec in self.results_df.loc[:, "fom_name"].values:
                foms.append(input_spec)
            else:
                dimensions.append(input_spec)

        if not dimensions:
            dimensions.append("experiment_name")

        raw_results = self.results_df[self.results_df.loc[:, "fom_name"].isin(foms)].copy()

        raw_results.loc[:, "Figure of Merit"] = (
            raw_results.loc[:, "fom_name"] + " (" + raw_results.loc[:, "fom_units"] + ")"
        )

        raw_results["fom_value"] = to_numeric_if_possible(raw_results["fom_value"])

        plot_col = "fom_value"
        if self.normalize:
            self.normalize_data(raw_results)
            plot_col = "normalized_fom_value"

        # TODO: remove pivot?
        compare_pivot = raw_results.pivot_table(
            plot_col, index=dimensions, columns="Figure of Merit"
        )
        self.output_df = compare_pivot

        # Pivot table aggregates values by mean. Check if results were aggregated and label them
        # Raw results have FOMs by row, pivot by columns, so multiply the pivot rows x cols
        # print(f'raw values = {len(raw_results)}  vs pivot values = {len(compare_pivot)} x {len(compare_pivot.columns)} ={len(compare_pivot) * len(compare_pivot.columns)}')

        # TODO: empty is silly here.. as is changing types
        perf_measure = foms
        scale_var = ""
        series = dimensions
        self.draw(perf_measure, scale_var, series)


class MultiLinePlot(ScalingPlotGenerator):
    series_to_plot = []

    def default_better(self):
        return BetterDirection.LOWER

    def draw(self, perf_measure, scale_var, series):
        if self.normalize:
            y_label = "Speedup"
        else:
            y_label = perf_measure

        super().draw(perf_measure, scale_var, series, y_label)

    def draw_multiline(self, perf_measure, scale_var, y_label):
        # TODO: add suffix 'higher/lower is better' to chart title based on better_direction
        title = f"{perf_measure} vs {scale_var}"
        logger.debug(f"Generating plot for {title}")

        # TODO: prep_draw method in subclass ScalingPlotGenerator, not this class
        fig, ax = self.prep_draw(perf_measure, scale_var)

        for series in self.output_df.loc[:, "series"].unique():
            series_data = self.output_df.query(f'series == "{series}"').copy()
            if self.normalize:
                ax.plot(
                    series_data.index,
                    "normalized_fom_value",
                    data=series_data,
                    marker="o",
                    label=f"{series} (Normalized)",
                )
            else:
                ax.plot(
                    series_data.index,
                    "fom_value",
                    data=series_data,
                    marker="o",
                    label=f"{series}",
                )

            if self.have_statistics:
                logger.debug("Adding fill lines for min and max")
                ax.fill_between(
                    series_data.index, "fom_value_min", "fom_value_max", data=series_data, alpha=0.2
                )

        ymin, ymax = ax.get_ylim()

        # TODO: the plot can get very compressed for log weak scaling plots
        if not self.logy:
            plt.ylim(0, ymax * 1.1)

        plt.legend(loc="upper left")

        ax.set_xticks(self.output_df.index.unique().tolist())
        ax.set_title(title, wrap=True)
        # This is to prevent x-axis labels overlapping but there's probably a better way
        if series_data.index.astype(str).str.len().max() > 4:
            ax.tick_params(axis="x", labelrotation=45)
            fig.tight_layout()
        ax.set_ylabel(y_label)
        ax.set_xlabel(scale_var)

        chart_filename = f"strong-scaling_{perf_measure}_vs_{scale_var}_all-series.png"
        self.write(fig, chart_filename)

    def generate_plot_data(self):
        super().generate_plot_data()

        perf_measure, scale_var, *additional_vars = self.spec

        if self.normalize:
            y_label = "Speedup"
        else:
            y_label = perf_measure

        self.draw_multiline(perf_measure, scale_var, y_label)

        # perf_measure, scale_var, *additional_vars = self.spec

        # # FOMs are by row, so select only rows with the perf_measure FOM
        # # raw_results = self.results_df.query(f'fom_name == "{perf_measure}"').copy()
        # # TODO this wont work for non-repeats
        # # raw_results = self.results_df.query(f'fom_name == "{perf_measure}" and fom_origin_type == "summary::mean"').copy()
        # raw_results = self.results_df.query(
        #     f'fom_name == "{fom}" and (fom_origin_type == "application" or fom_origin_type == "modifier" or fom_origin_type == "summary::mean")'
        # ).copy()

        # raw_results.loc[:, "series"] = raw_results.loc[:, self.split_by]

        # # TODO: check this does what we want and generates unique results/groups
        # for series in raw_results.loc[:, "series"].unique():
        #     # TODO: query should support fom_origin_type
        #     selected = raw_results.query(f'series == "{series}"')
        #     pretty_results = selected.groupby(additional_vars + ["series"] + ["fom_name"]).agg(
        #         {"fom_value": [np.min, np.max]}
        #     )
        #     group_results = selected.groupby(additional_vars + ["series"] + ["fom_name"])
        #     for name, group in group_results:
        #         group["fom_value"] = to_numeric_if_possible(group["fom_value"])
        #         group[scale_var] = to_numeric_if_possible(group[scale_var])
        #         group = group.set_index(scale_var)
        #         self.series_to_plot.append((name, group))
        #     self.draw(perf_measure, scale_var, series)


def get_reports_path():
    """Returns current directory of ramble-created reports"""
    path_in_config = ramble.config.get("config:report_dirs")
    if not path_in_config:
        logger.die(
            "No config:report_dirs setting found in configuration. To add one,  "
            'use command: ramble config add "config:report_dirs:~/.ramble/reports"'
        )

    report_path = ramble.util.path.canonicalize_path(str(path_in_config))
    return report_path


def make_report(results_df, ws_name, args):
    dt = datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    report_dir_root = get_reports_path()

    report_name = f"{ws_name}.{dt}"
    report_dir_path = os.path.join(report_dir_root, report_name)
    fs.mkdirp(report_dir_path)
    pdf_path = os.path.join(report_dir_path, f"{report_name}.pdf")

    with PdfPages(pdf_path) as pdf_report:

        plot_factory = PlotFactory()
        plot_generators = plot_factory.create_plot_generators(
            args, report_dir_path, pdf_report, results_df
        )

        for plot in plot_generators:
            plot.generate_plot_data()

    if os.path.isfile(pdf_path):
        logger.msg(
            "Report generated successfully. A PDF summary is available at:\n" f"    {pdf_path}"
        )
        logger.msg("Individual chart images are available at:\n" f"    {report_dir_path}")
