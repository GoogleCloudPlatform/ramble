# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
import datetime
from enum import Enum
import os
import re

import llnl.util.filesystem as fs
import spack.util.spack_yaml as syaml

import ramble.cmd.results
import ramble.cmd.workspace
import ramble.config
import ramble.filters
from ramble.keywords import keywords
import ramble.pipeline
import ramble.util.path
from ramble.util.foms import BetterDirection, FomType
from ramble.util.logger import logger
from ramble.util.file_util import create_symlink

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    import pandas as pd
except ModuleNotFoundError:
    logger.die("matplotlib or pandas was not found. Ensure requirements.txt are installed.")


class ReportVars(Enum):
    BETTER_DIRECTION = "better_direction"
    CONTEXT = "context"
    FOM_NAME = "fom_name"
    FOM_ORIGIN = "fom_origin"
    FOM_ORIGIN_TYPE = "fom_origin_type"
    FOM_UNITS = "fom_units"
    FOM_VALUE = "fom_value"
    FOM_VALUE_MIN = "fom_value_min"
    FOM_VALUE_MAX = "fom_value_max"
    IDEAL_PERF_VALUE = "ideal_perf_value"
    NORMALIZED_FOM_VALUE = "normalized_fom_value"
    SERIES = "series"


_FOM_DICT_MAPPING = {
    "name": ReportVars.FOM_NAME.value,
    "value": ReportVars.FOM_VALUE.value,
    "units": ReportVars.FOM_UNITS.value,
    "origin": ReportVars.FOM_ORIGIN.value,
    "origin_type": ReportVars.FOM_ORIGIN_TYPE.value,
}

INVENTORY_FILENAME = "inventory.yaml"


def to_numeric_if_possible(series):
    """Try to convert a Pandas series to numeric, or return the series unchanged."""
    try:
        return pd.to_numeric(series)
    except (ValueError, TypeError):
        return series


def get_direction_suffix(self):
    if self == BetterDirection.HIGHER:
        return " (Higher is Better)"
    if self == BetterDirection.LOWER:
        return " (Lower is Better)"
    else:
        return ""


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
    if int(experiment["RAMBLE_VARIABLES"][keywords.repeat_index]) > 0:
        return True
    else:
        return False


def prepare_data(results: dict, where_query) -> pd.DataFrame:
    """Creates a Pandas DataFrame from the results dictionary to use for reports.

    Transforms nested results dictionary into a flat dataframe. Each row equals
    one FOM from one context of one experiment, with columns including
    associated experiment variables (except paths and commands).
    """

    unnest_context = []
    skip_exps = []
    # first unnest dictionaries
    for exp in results["experiments"]:
        if exp["name"] in skip_exps or is_repeat_child(exp):
            logger.debug(f"Skipping import of experiment {exp['name']}")
            continue

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
                    # Expand to one row/FOM/context w/ a copy of the experiment vars and metadata
                    exp_copy = copy.deepcopy(exp)

                    # Remove context dict and add the current FOM values
                    exp_copy.pop("CONTEXTS")
                    exp_copy[ReportVars.CONTEXT.value] = context["name"]
                    for name, val in fom.items():
                        if name in _FOM_DICT_MAPPING.keys():
                            exp_copy[_FOM_DICT_MAPPING[name]] = val
                        elif name == "fom_type":
                            exp_copy["fom_type"] = FomType.from_str(fom["fom_type"]["name"])
                            exp_copy[ReportVars.BETTER_DIRECTION.value] = BetterDirection.from_str(
                                fom["fom_type"][ReportVars.BETTER_DIRECTION.value]
                            )

                        # older data exports may not have fom_type stored
                        if "fom_type" not in exp_copy:
                            exp_copy["fom_type"] = FomType.UNDEFINED
                            exp_copy[ReportVars.BETTER_DIRECTION.value] = (
                                BetterDirection.INDETERMINATE
                            )

                    # Exclude vars that aren't needed for analysis, mainly paths and commands
                    dir_regex = r"_dir$"
                    path_regex = r"_path$"
                    vars_to_ignore = [
                        keywords.batch_submit,
                        keywords.log_file,
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

    def determine_plot_type(self, args):
        plot_types = [
            (args.strong_scaling, StrongScalingPlot),
            (args.weak_scaling, WeakScalingPlot),
            (args.compare, ComparisonPlot),
            (args.foms, FomPlot),
            (args.multi_line, MultiLinePlot),
        ]
        for plot_type, plot_class in plot_types:
            if plot_type:
                return (plot_type, plot_class)

    def create_plot_generator(self, args, report_dir_path, results_df):
        normalize = args.normalize
        logx = args.logx
        logy = args.logy
        split_by = args.split_by

        spec, plot_class = self.determine_plot_type(args)

        if spec:
            plot = plot_class(
                spec,
                normalize,
                report_dir_path,
                results_df,
                logx,
                logy,
                split_by,
            )
            return plot

        logger.die("No plots requested. Please specify required plots or see help (-h)")


class PlotGenerator:
    def __init__(self, spec, normalize, report_dir_path, results_df, logx, logy, split_by):
        self.normalize = normalize
        self.spec = spec
        self.report_dir_path = report_dir_path
        self.inventory = {"files": []}
        self.figsize = [12, 8]

        self.results_df = results_df
        self.output_df = pd.DataFrame()

        self.logx = logx
        self.logy = logy

        self.split_by = split_by

        self.have_statistics = False
        self.better_direction = BetterDirection.INDETERMINATE

    def normalize_data(
        self,
        data,
        scale_to_index=False,
        to_col=ReportVars.NORMALIZED_FOM_VALUE.value,
        from_col=ReportVars.FOM_VALUE.value,
    ):
        if data[from_col].iloc[0] == 0:
            raise ArithmeticError(
                "Unable to normalize data. The first value in the series cannot be zero."
            )
        else:
            # Adjusts first y-value to first scale var when >1 (e.g., speedup for 2+ nodes = 2)
            if scale_to_index:
                # Performs inplace edit on data, no need to return
                data.loc[:, to_col] = (
                    data.loc[:, from_col] / data[from_col].iloc[0]
                ) * data.index[0]
            else:
                data.loc[:, to_col] = data.loc[:, from_col] / data[from_col].iloc[0]

    def add_minmax_data(self, selected_data, min_data, max_data, scale_var):
        """When using summary statistics from repeats, adds columns fom_value_min and fom_value_max
        to the selected data.
        """
        min_data.loc[:, scale_var] = to_numeric_if_possible(min_data[scale_var])
        min_data = min_data.set_index(scale_var)
        max_data.loc[:, scale_var] = to_numeric_if_possible(max_data[scale_var])
        max_data = max_data.set_index(scale_var)

        selected_data.loc[:, ReportVars.FOM_VALUE_MIN.value] = to_numeric_if_possible(
            min_data[ReportVars.FOM_VALUE.value]
        )
        selected_data.loc[:, ReportVars.FOM_VALUE_MAX.value] = to_numeric_if_possible(
            max_data[ReportVars.FOM_VALUE.value]
        )

        if self.normalize:
            self.normalize_data(
                selected_data,
                scale_to_index=True,
                to_col=ReportVars.FOM_VALUE_MIN.value,
                from_col=ReportVars.FOM_VALUE_MIN.value,
            )
            self.normalize_data(
                selected_data,
                scale_to_index=True,
                to_col=ReportVars.FOM_VALUE_MAX.value,
                from_col=ReportVars.FOM_VALUE_MAX.value,
            )

    def get_inventory_path(self):
        return os.path.join(self.report_dir_path, INVENTORY_FILENAME)

    def add_to_inventory(self, filename):
        """Adds a filename to the inventory.

        Args:
            filename: filename to add to inventory.
        """
        self.inventory["files"].append(filename)

    def write_inventory(self):
        with open(self.get_inventory_path(), "w+") as f:
            syaml.dump(self.inventory, stream=f)

    def draw(self, perf_measure, scale_var, series, pdf_report, y_label=None):
        series_data = self.output_df.query(f'series == "{series}"').copy()

        title = (
            f"{perf_measure} vs {scale_var} for {series}"
            f"{get_direction_suffix(self.better_direction)}"
        )
        logger.debug(f"Generating plot for {title}")

        # TODO: prep_draw method in subclass ScalingPlotGenerator, not this class
        fig, ax = self.prep_draw(perf_measure, scale_var)

        if self.normalize:
            ax.plot(
                series_data.index,
                ReportVars.NORMALIZED_FOM_VALUE.value,
                data=series_data,
                marker="o",
                label=f"{perf_measure} (Normalized)",
            )
        else:
            ax.plot(
                series_data.index,
                ReportVars.FOM_VALUE.value,
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
                series_data.index,
                ReportVars.FOM_VALUE_MIN.value,
                ReportVars.FOM_VALUE_MAX.value,
                data=series_data,
                alpha=0.2,
            )

        try:
            ax.plot(
                series_data.index,
                ReportVars.IDEAL_PERF_VALUE.value,
                data=series_data,
                label="Ideal Value",
            )
        except ValueError:
            logger.debug("Failed to plot ideal_perf_value. Series not found.")

        plt.legend(loc="upper left")

        ax.set_xticks(series_data.index.unique().tolist())
        ax.set_title(title, wrap=True)
        if y_label:
            ax.set_ylabel(y_label)
        ax.set_xlabel(scale_var)

        # Rotate to prevent long x-axis labels overlapping. There's probably a better way
        if series_data.index.astype(str).str.len().max() > 4:
            ax.tick_params(axis="x", labelrotation=45)
            fig.tight_layout()

        chart_filename = f"strong-scaling_{perf_measure}_vs_{scale_var}_{series}.png"
        self.write(fig, chart_filename, pdf_report)

    def draw_filler(self, perf_measure, scale_var, series, exception, pdf_report):
        # FIXME: DRY THIS
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
        self.write(fig, chart_filename, pdf_report)

    def validate_spec(self, chart_spec):
        """Validates that the FOMs and variables in the chart spec are in the results data."""
        for var in chart_spec:
            if (
                var not in self.results_df.columns
                and var not in self.results_df.loc[:, ReportVars.FOM_NAME.value].values
            ):
                logger.debug(f"Available options: {self.results_df.loc[:, 'fom_name'].unique()}")
                logger.die(f"{var} was not found in the results data.")

    def write(self, fig, filename, pdf_report):
        filename = filename.replace(" ", "-")
        plt.savefig(os.path.join(self.report_dir_path, filename))
        self.add_to_inventory(filename)
        pdf_report.savefig(fig)
        plt.close(fig)


class ScalingPlotGenerator(PlotGenerator):
    def generate_plot_data(self, pdf_report):
        """Creates a dataframe for plotting line charts with scaling var on x axis,
        and performance variable on y axis."""
        self.validate_spec(self.spec)

        perf_measure, scale_var, *additional_vars = self.spec

        # FOMs are by row, so select only rows with the perf_measure FOM
        results = self.results_df.query(f'fom_name == "{perf_measure}"').copy()

        # Determine which direction is 'better', or 'INDETERMINATE' if missing or ambiguous data
        if len(results.loc[:, ReportVars.BETTER_DIRECTION.value].unique()) == 1:
            self.better_direction = results.loc[:, ReportVars.BETTER_DIRECTION.value].unique()[0]

        # TODO: this needs to support a list for split_by
        # TODO: this currently gets overwritten by series, below
        results.loc[:, ReportVars.SERIES.value] = results.loc[:, self.split_by]

        if additional_vars:
            # TODO: this would be nicer as a group by
            results.loc[:, ReportVars.SERIES.value] = (
                results.loc[:, ReportVars.SERIES.value]
                + "_x_"
                + results[additional_vars].agg("_x_".join, axis=1)
            )

        for series in results.loc[:, ReportVars.SERIES.value].unique():

            # TODO: this needs to account for repeats in a more elegant way
            series_results = results.query(
                f'series == "{series}" and (fom_origin_type == "application" '
                'or fom_origin_type == "modifier" or fom_origin_type == "summary::mean")'
            ).copy()

            series_results.loc[:, ReportVars.FOM_VALUE.value] = to_numeric_if_possible(
                series_results[ReportVars.FOM_VALUE.value]
            )
            series_results.loc[:, scale_var] = to_numeric_if_possible(series_results[scale_var])
            series_results = series_results.set_index(scale_var)

            self.validate_data(series_results)

            if self.normalize:
                try:
                    self.normalize_data(series_results, scale_to_index=True)
                except ArithmeticError as e:
                    logger.warn(e)
                    self.draw_filler(perf_measure, scale_var, series, e, pdf_report)
                    continue

            if series_results.loc[:, ReportVars.FOM_ORIGIN_TYPE.value].iloc[0] == "summary::mean":
                self.have_statistics = True

            if self.have_statistics:
                series_min = results.query(
                    f'series == "{series}" and fom_origin_type == "summary::min"'
                ).copy()
                series_max = results.query(
                    f'series == "{series}" and fom_origin_type == "summary::max"'
                ).copy()
                self.add_minmax_data(series_results, series_min, series_max, scale_var)

            series_results = self.add_idealized_data(results, series_results)
            self.output_df = pd.concat([self.output_df, series_results])

            self.draw(perf_measure, scale_var, series, pdf_report)

    def add_idealized_data(self, raw_results, selected_data):
        # Skip if no better direction, but override in subclasses when there's a default_better
        if (
            self.better_direction == BetterDirection.INDETERMINATE
            or self.better_direction == BetterDirection.INAPPLICABLE
        ):
            return selected_data

        if self.normalize:
            first_perf_value = selected_data[ReportVars.NORMALIZED_FOM_VALUE.value].iloc[0]
        else:
            first_perf_value = selected_data[ReportVars.FOM_VALUE.value].iloc[0]

        if first_perf_value == 0:
            logger.warn(
                "Unable to calculate idealized data. The first value in the series cannot be zero."
            )
            return selected_data

        logger.debug(f"Normalizing data (by {first_perf_value})")

        selected_data.loc[:, ReportVars.IDEAL_PERF_VALUE.value] = first_perf_value

        if self.better_direction == BetterDirection.LOWER:
            selected_data[ReportVars.IDEAL_PERF_VALUE.value] = selected_data.loc[
                :, ReportVars.IDEAL_PERF_VALUE.value
            ] / (
                selected_data.index / selected_data.index[0]  # set baseline scaling var to 1
            )
        elif self.better_direction == BetterDirection.HIGHER:
            selected_data[ReportVars.IDEAL_PERF_VALUE.value] = selected_data.loc[
                :, ReportVars.IDEAL_PERF_VALUE.value
            ] * (selected_data.index / selected_data.index[0])

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
            logger.die("Attempting to plot non-unique data. Please reduce data and try again")

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
    plot_type = "weak_scaling"

    def draw(self, perf_measure, scale_var, series, pdf_report):
        y_label = perf_measure

        super().draw(perf_measure, scale_var, series, pdf_report, y_label)

    def add_idealized_data(self, raw_results, selected_data):
        selected_data = super().add_idealized_data(raw_results, selected_data)

        if ReportVars.IDEAL_PERF_VALUE.value in selected_data.columns:
            selected_data.loc[:, ReportVars.IDEAL_PERF_VALUE.value] = selected_data[
                ReportVars.IDEAL_PERF_VALUE.value
            ].iloc[0]
        return selected_data


class StrongScalingPlot(ScalingPlotGenerator):
    plot_type = "strong_scaling"

    def default_better(self):
        if self.normalize:
            return BetterDirection.HIGHER
        else:
            return BetterDirection.LOWER

    def add_idealized_data(self, raw_results, selected_data):
        if self.better_direction is BetterDirection.INDETERMINATE:
            self.better_direction = self.default_better()

        return super().add_idealized_data(raw_results, selected_data)

    def normalize_data(
        self,
        data,
        scale_to_index=True,
        to_col=ReportVars.NORMALIZED_FOM_VALUE.value,
        from_col=ReportVars.FOM_VALUE.value,
    ):
        super().normalize_data(data, scale_to_index, to_col=to_col, from_col=from_col)

    def draw(self, perf_measure, scale_var, series, pdf_report):
        y_label = perf_measure

        super().draw(perf_measure, scale_var, series, pdf_report, y_label)


class FomPlot(PlotGenerator):
    plot_type = "foms"

    def generate_plot_data(self, pdf_report):
        results = self.results_df
        all_foms = results.loc[:, ReportVars.FOM_NAME.value].unique()
        for fom in all_foms:
            series_results = results.query(
                f'fom_name == "{fom}" and (fom_origin_type == "application" or '
                'fom_origin_type == "modifier" or fom_origin_type == "summary::mean" or '
                'fom_origin_type == "summary::n_total_repeats")'
            ).copy()

            scale_var = "simplified_experiment_namespace"

            series_results.loc[:, ReportVars.FOM_VALUE.value] = to_numeric_if_possible(
                series_results[ReportVars.FOM_VALUE.value]
            )

            series_results.loc[:, scale_var] = to_numeric_if_possible(series_results[scale_var])

            series_results = series_results.set_index(scale_var)

            if self.normalize:
                self.normalize_data(series_results, scale_to_index=True)

            if series_results.loc[:, ReportVars.FOM_ORIGIN_TYPE.value].iloc[0] == "summary::mean":
                self.have_statistics = True

            if self.have_statistics:
                series_min = results.query(
                    f'fom_name == "{fom}" and fom_origin_type == "summary::min"'
                ).copy()
                series_max = results.query(
                    f'fom_name == "{fom}" and fom_origin_type == "summary::max"'
                ).copy()
                self.add_minmax_data(series_results, series_min, series_max, scale_var)

            self.output_df = series_results

            unit = series_results.loc[:, ReportVars.FOM_UNITS.value].iloc[0]

            perf_measure = fom
            series = "experiment_name"
            self.draw(perf_measure, scale_var, series, unit, pdf_report)

    # TODO: dry bar plot drawing
    def draw(self, perf_measure, scale_var, series, unit, pdf_report):

        self.output_df[ReportVars.FOM_VALUE.value] = to_numeric_if_possible(
            self.output_df[ReportVars.FOM_VALUE.value]
        )

        from pandas.api.types import is_numeric_dtype

        if not is_numeric_dtype(self.output_df[ReportVars.FOM_VALUE.value]):
            logger.warn(f"Skipping drawing of non numeric FOM: {perf_measure}")
            return

        # TODO: this should leverage the available min/max to add candle sticks
        ax = self.output_df.plot(y=ReportVars.FOM_VALUE.value, kind="bar", figsize=self.figsize)
        fig = ax.get_figure()

        # ax.set_label('Label via method')
        legend_text = perf_measure
        if len(unit) > 0:
            legend_text = f"{perf_measure} ({unit})"

        ax.legend([legend_text])

        # If all FOMs are either higher or lower is better, add it to chart title
        ax.set_title(f"{perf_measure} by experiment", wrap=True)

        # FIXME: Rotate to prevent long x-axis labels overlapping. This can make the chart
        # very small but experiment names are readable (for smaller number of experiments)
        if self.output_df.index.astype(str).str.len().max() > 4:
            ax.tick_params(axis="x", labelrotation=90)
            fig.tight_layout()

        chart_filename = f"foms_{perf_measure}_by_experiments.png"
        self.write(fig, chart_filename, pdf_report)


class ComparisonPlot(PlotGenerator):
    plot_type = "comparison"

    def draw(self, perf_measure, scale_var, series, pdf_report):
        ax = self.output_df.plot(kind="bar", figsize=self.figsize)
        fig = ax.get_figure()

        # If all FOMs are either higher or lower is better, add it to chart title
        title_suffix = ""
        ax.set_title(
            f'{" vs ".join(perf_measure)} by {" and ".join(series)} {title_suffix}', wrap=True
        )

        # FIXME: this has a hard time fitting well on screen
        fig.tight_layout()

        chart_filename = f'{"_vs_".join(perf_measure)}_by_{"_and_".join(series)}.png'
        self.write(fig, chart_filename, pdf_report)

    def generate_plot_data(self, pdf_report):
        # Break out input args into FOMs and dimensions
        foms = []
        dimensions = []

        for input_spec in self.spec:
            if input_spec in self.results_df.loc[:, ReportVars.FOM_NAME.value].values:
                foms.append(input_spec)
            else:
                dimensions.append(input_spec)

        if not dimensions:
            dimensions.append("experiment_name")

        raw_results = self.results_df[
            self.results_df.loc[:, ReportVars.FOM_NAME.value].isin(foms)
        ].copy()

        raw_results.loc[:, "Figure of Merit"] = (
            raw_results.loc[:, ReportVars.FOM_NAME.value]
            + " ("
            + raw_results.loc[:, ReportVars.FOM_UNITS.value]
            + ")"
        )

        raw_results[ReportVars.FOM_VALUE.value] = to_numeric_if_possible(
            raw_results[ReportVars.FOM_VALUE.value]
        )

        plot_col = ReportVars.FOM_VALUE.value
        if self.normalize:
            self.normalize_data(raw_results)
            plot_col = ReportVars.NORMALIZED_FOM_VALUE.value

        # TODO: remove pivot?
        compare_pivot = raw_results.pivot_table(
            plot_col, index=dimensions, columns="Figure of Merit"
        )
        self.output_df = compare_pivot

        # Pivot table aggregates values by mean. Check if results were aggregated and label them
        # Raw results have FOMs by row, pivot by columns, so multiply the pivot rows x cols
        # print(f'raw values = {len(raw_results)}  vs pivot values = {len(compare_pivot)} x
        # {len(compare_pivot.columns)} ={len(compare_pivot) * len(compare_pivot.columns)}')

        perf_measure = foms
        scale_var = ""
        series = dimensions
        self.draw(perf_measure, scale_var, series, pdf_report)


class MultiLinePlot(ScalingPlotGenerator):
    plot_type = "multi_line"
    series_to_plot = []

    def default_better(self):
        return BetterDirection.HIGHER

    def normalize_data(
        self,
        data,
        scale_to_index=True,
        to_col=ReportVars.NORMALIZED_FOM_VALUE.value,
        from_col=ReportVars.FOM_VALUE.value,
    ):
        super().normalize_data(
            data,
            scale_to_index,
            to_col=to_col,
            from_col=from_col,
        )

    def draw_multiline(self, perf_measure, scale_var, pdf_report, y_label):
        # TODO: add suffix 'higher/lower is better' to chart title based on better_direction
        title = f"{perf_measure} vs {scale_var}"
        logger.debug(f"Generating plot for {title}")

        # TODO: prep_draw method in subclass ScalingPlotGenerator, not this class
        fig, ax = self.prep_draw(perf_measure, scale_var)

        for series in self.output_df.loc[:, ReportVars.SERIES.value].unique():
            series_data = self.output_df.query(f'series == "{series}"').copy()
            if self.normalize:
                ax.plot(
                    series_data.index,
                    ReportVars.NORMALIZED_FOM_VALUE.value,
                    data=series_data,
                    marker="o",
                    label=f"{series} (Normalized)",
                )
            else:
                ax.plot(
                    series_data.index,
                    ReportVars.FOM_VALUE.value,
                    data=series_data,
                    marker="o",
                    label=f"{series}",
                )

            if self.have_statistics:
                logger.debug("Adding fill lines for min and max")
                ax.fill_between(
                    series_data.index,
                    ReportVars.FOM_VALUE_MIN.value,
                    ReportVars.FOM_VALUE_MAX.value,
                    data=series_data,
                    alpha=0.2,
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

        chart_filename = f"multi_line_{perf_measure}_vs_{scale_var}_all-series.png"
        self.write(fig, chart_filename, pdf_report)

    def generate_plot_data(self, pdf_report):
        super().generate_plot_data(pdf_report)

        perf_measure, scale_var, *additional_vars = self.spec
        y_label = perf_measure

        self.draw_multiline(perf_measure, scale_var, pdf_report, y_label)


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

    report_base = f"{ws_name}"
    report_name = f"{report_base}.{dt}"
    report_dir_path = os.path.join(report_dir_root, report_name)
    fs.mkdirp(report_dir_path)

    plot_factory = PlotFactory()
    plot = plot_factory.create_plot_generator(args, report_dir_path, results_df)
    plot_type = plot.plot_type

    pdf_filename = f"{report_name}.{plot_type}.pdf"
    pdf_path = os.path.join(report_dir_path, pdf_filename)
    with PdfPages(pdf_path) as pdf_report:
        plot.generate_plot_data(pdf_report)
        plot.add_to_inventory(pdf_filename)

    if os.path.isfile(pdf_path):
        plot.write_inventory()
        symlinks_created = []

        for base in report_base, "reports":
            # Symlink specific workspace latest file
            latest_file = f"{base}.latest.pdf"
            latest_path = os.path.join(report_dir_root, latest_file)
            symlinks_created.append(latest_path)
            create_symlink(pdf_path, latest_path)

            latest_file = f"{base}.{plot_type}.latest.pdf"
            latest_path = os.path.join(report_dir_root, latest_file)
            symlinks_created.append(latest_path)
            create_symlink(pdf_path, latest_path)

        logger.all_msg("Report generated successfully. A PDF summary is available at:")
        logger.all_msg(f"  {pdf_path}")
        logger.all_msg("Individual chart images are available at:")
        logger.all_msg(f"  {report_dir_path}")
        logger.all_msg("Symlinks updated:")
        for path in symlinks_created:
            logger.all_msg(f"  {path}")
