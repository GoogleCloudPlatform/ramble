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
    """Try to convert a Pandas series to numeric, or return the series unchanged.
    """
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
        # TODO: why does this call back into cmd?
        if os.path.exists(args.file):
            results_dict = ramble.cmd.results.import_results_file(args.file)
        else:
            logger.die(f"Cannot find file {args.file}")
    else:
        ramble_ws = ramble.cmd.find_workspace_path(args)

        if not ramble_ws:
            logger.die("ramble results report requires either a results filename, "
                       "a command line workspace, or an active workspace")

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
            logger.die("No JSON or YAML results file was found. Please run "
                       "'ramble workspace analyze -f json'.")
    return results_dict


def prepare_data(results: dict) -> pd.DataFrame:
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

    unnest_context = []
    skip_exps = []
    # first unnest dictionaries
    for exp in results['experiments']:
        if exp['RAMBLE_STATUS'] != 'SUCCESS' or exp['name'] in skip_exps:
            logger.debug(f"Skipping import of experiment {exp['name']}")
            continue
        else:
            # For repeat experiments, use summary stats from base exp and skip repeats
            # Repeats are sequenced after base exp
            if exp.get('N_REPEATS', 0) > 0:
                # Generate repeat experiment names in order to skip them explicitly
                exp_name = exp['name']
                for n in range(1, exp['N_REPEATS'] + 1):
                    if ".chain" in exp_name:
                        insert_idx = exp_name.index(".chain")
                        repeat_exp_name = exp_name[:insert_idx] + f".{n}" + exp_name[insert_idx:]
                        skip_exps.append(repeat_exp_name)
                    else:
                        skip_exps.append(exp_name + f".{n}")

            for context in exp['CONTEXTS']:
                for fom in context['foms']:
                    # Expand to one row per FOM per context w/ a copy of the experiment vars and metadata
                    exp_copy = copy.deepcopy(exp)

                    # Remove context dict and add the current FOM values
                    # TODO: Can we clean this partial copy with a class?
                    exp_copy.pop('CONTEXTS')
                    exp_copy['context'] = context['display_name']
                    exp_copy['fom_name'] = fom['name']
                    exp_copy['fom_value'] = fom['value']
                    exp_copy['fom_units'] = fom['units']
                    exp_copy['fom_origin'] = fom['origin']
                    exp_copy['fom_origin_type'] = fom['origin_type']
                    print(fom)
                    if 'fom_type' in fom.keys():
                        exp_copy['better_direction'] = fom['fom_type']['better_direction']
                    else:  # if using older data file without fom_type
                        exp_copy['better_direction'] = 'INDETERMINATE'

                    # Flatten final vars dict and drop raw vars dict
                    for key in ["RAMBLE_VARIABLES", "RAMBLE_RAW_VARIABLES"]:
                        if key in exp_copy:
                            exp_copy.pop(key)

                    # Exclude vars that aren't needed for analysis, mainly paths and commands
                    dir_regex = r"_dir$"
                    path_regex = r"_path$"
                    vars_to_ignore = [
                        'batch_submit',
                        'log_file',
                        'command',
                        'execute_experiment',
                    ]
                    for key, value in exp['RAMBLE_VARIABLES'].items():
                        if key in vars_to_ignore:
                            continue
                        if re.search(dir_regex, key):
                            continue
                        if re.search(path_regex, key):
                            continue
                        exp_copy[key] = value

                    unnest_context.append(exp_copy)

    results_df = pd.DataFrame.from_dict(unnest_context)
    #pd.DataFrame.to_json(results_df, 'prepare_data_results.json')

    return results_df


class PlotFactory:
    def create_plot_generators(self, args, report_dir_path, pdf_report):
        plots = []
        normalize = args.normalize

        if args.strong_scaling:
            spec = args.strong_scaling
            plots.append( StrongScalingPlot(spec, normalize, report_dir_path, pdf_report) )

        if args.weak_scaling:
            spec = args.weak_scaling
            plots.append( WeakScalingPlot(spec, normalize, report_dir_path, pdf_report) )

        if args.compare:
            spec = args.compare
            plots.append( ComparisonPlot(spec, normalize, report_dir_path, pdf_report) )

        if args.foms:
            spec = args.foms
            plots.append( FomPlot(spec, normalize, report_dir_path, pdf_report) )

        if not plots:
            # TODO: should this be checked in cmd?
            # TODO: make this error more descriptive
            logger.die("No plots requested. Please specify required plots")
        else:
            return plots


class PlotGenerator:
    def __init__(self, spec, normalize, report_dir_path, pdf_report):
        self.normalize = normalize
        self.spec = spec
        self.report_dir_path = report_dir_path
        self.pdf_report = pdf_report

    def normalize_data(self, data, speedup=False):
        # Performs inplace edit on data, no need to return
        if speedup:
            data.loc[:, 'normalized_fom_value'] = data['fom_value'].iloc[0] / data.loc[:, 'fom_value']
        else:
            data.loc[:, 'normalized_fom_value'] = data.loc[:, 'fom_value'] / data['fom_value'].iloc[0]

    def generate_plot(self, results_df):
        for chart_spec in self.spec:
            self.validate_spec(results_df, chart_spec)

    def validate_spec(self, results_df, chart_spec):
        """Validates that the FOMs and variables in the chart spec are in the results data."""
        for var in chart_spec:
            if var not in results_df.columns and var not in results_df.loc[:, 'fom_name'].values:
                logger.die(f'{var} was not found in the results data.')

    def write(self, fig, filename):
        filename = filename.replace(" ", "-")
        plt.savefig(os.path.join(self.report_dir_path, filename))
        self.pdf_report.savefig(fig)
        plt.close(fig)


class ScalingPlotGenerator(PlotGenerator):
    def add_ideal_line(self, raw_results, selected_data, better_direction):

        if self.normalize:
            first_perf_value = selected_data['normalized_fom_value'].iloc[0]
        else:
            first_perf_value = selected_data['fom_value'].iloc[0]

        selected_data.loc[:, 'ideal_perf_value'] = first_perf_value

        if better_direction == 'LOWER' or better_direction == BetterDirection.LOWER:
            selected_data['ideal_perf_value'] = selected_data.loc[:, 'ideal_perf_value'] / (selected_data.index)
        elif better_direction == 'HIGHER' or better_direction == BetterDirection.HIGHER:
            selected_data['ideal_perf_value'] = selected_data.loc[:, 'ideal_perf_value'] * (selected_data.index)

        print(selected_data)
        return selected_data

    def generate_plot(self, results_df):
        super().generate_plot(results_df)

        # TODO: this could be in init?
        for chart_spec in self.spec:
            if len(chart_spec) < 2:
                logger.die('Scaling plot requires two arguments: '
                           'performance metric and scaling metric')


class WeakScalingPlot(ScalingPlotGenerator):
    def default_better(self):
        # TODO: By default we expect this to be flat...
        return BetterDirection.LOWER

    def add_ideal_line(self, raw_results, selected_data, better_direction = BetterDirection.INDETERMINATE):
        if better_direction is BetterDirection.INDETERMINATE:
            better_direction = self.default_better()

        selected_data = super().add_ideal_line(raw_results, selected_data, better_direction)

        selected_data.loc[:, 'ideal_perf_value'] = selected_data['ideal_perf_value'].iloc[0]
        return selected_data

    def generate_plot(self, results_df):
        super().generate_plot(results_df)

        for chart_spec in self.spec:
            perf_measure, scale_var, *additional_vars = chart_spec

            # FOMs are by row, so select only rows with the perf_measure FOM
            raw_results = results_df.query(f'fom_name == "{perf_measure}"').copy()

            raw_results.loc[:, 'series'] = raw_results.loc[:, 'simplified_workload_namespace']
            if additional_vars:
                for var in additional_vars:
                    raw_results.loc[:, 'series'] = raw_results.loc[:, 'series'] + '_x_' + var

            for series in raw_results.loc[:, 'series'].unique():
                series_results = raw_results.query(f'series == "{series}"')
                selected = series_results.loc[:, [f'{scale_var}', 'fom_value']]
                selected['fom_value'] = to_numeric_if_possible(pd.to_numeric(raw_results['fom_value']))
                selected[scale_var] = to_numeric_if_possible(pd.to_numeric(raw_results[scale_var]))

                selected = selected.set_index(scale_var)

                fig, ax = plt.subplots()

                col_to_plot = 'fom_value'

                if self.normalize:
                    self.normalize_data(selected)
                    ax.set_ylabel('Efficiency')
                    col_to_plot = 'normalized_fom_value'
                else:
                    first_perf_value = selected['fom_value'].iloc[0]
                    ax.set_ylabel(f'{perf_measure}')

                # TODO: this might go the wrong way post abstraction, but ideal scaling on weak is confusing.. since it should be flat (and can easily be fixed in the class hierarchy
                selected = self.add_ideal_line(series_results, selected)

                ax.plot('ideal_perf_value', data=selected)
                ax.plot(col_to_plot, data=selected, marker='o')
                #ax.plot(f'{scale_var}', 'ideal_perf_value', data=selected)
                #ax.plot(f'{scale_var}', col_to_plot, data=selected, marker='o')

                ax.set_xlabel(scale_var)
                plt.legend(loc="upper left")

                # TODO: add a way to enable log axix
                # ax.set_xscale('log')

                #ax.set_xticks(raw_results.query(f'series == "{series}"')[f'{scale_var}'].unique().tolist())
                ax.set_xticks(selected.index.unique().tolist())
                ax.set_title(f'Weak Scaling: {perf_measure} vs {scale_var} for {series}', wrap=True)

                chart_filename = f'weak-scaling_{perf_measure}_vs_{scale_var}_{series}.png'
                self.write(fig, chart_filename)


class StrongScalingPlot(ScalingPlotGenerator):
    # TODO: I'm not super sure why david wanted this, but it will be missing some data as-iis
    def show_table(self, ax, scale_pivot):
        ax.axis('tight')
        ax.axis('off')
        ax.table(cellText=scale_pivot.values, colLabels=scale_pivot.columns, loc='center')

    def default_better(self):
        if self.normalize:
            return BetterDirection.HIGHER
        else:
            return BetterDirection.LOWER

    def add_ideal_line(self, raw_results, selected_data, better_direction=BetterDirection.INDETERMINATE):
        # TODO: we need to set the better direction to be the oposite when normalized
        if better_direction is BetterDirection.INDETERMINATE:
            better_direction = self.default_better()

        return super().add_ideal_line(raw_results, selected_data, better_direction)

    def generate_plot(self, results_df):
        super().generate_plot(results_df)
        for chart_spec in self.spec:

            perf_measure, scale_var, *additional_vars = chart_spec

            # FOMs are by row, so select only rows with the perf_measure FOM
            perf_measure_results = results_df.query(f'fom_name == "{perf_measure}"').copy()

            # Determine which direction is 'better', or 'INDETERMINATE' if missing or ambiguous data
            better_direction = BetterDirection.INDETERMINATE
            if len(perf_measure_results.loc[:, 'better_direction'].unique()) == 1:
                better_direction = perf_measure_results.loc[:, 'better_direction'].unique()[0]

            # TODO: Take magic strings like 'application_namespace' from an ENUM
            perf_measure_results.loc[:, 'series'] = perf_measure_results.loc[:, 'application_namespace'] + '_' + perf_measure_results.loc[:, 'workload_name']

            # Break data down into series using app, workload, and vars input by user
            if additional_vars:
                perf_measure_results.loc[:, 'series'] = perf_measure_results.loc[:, 'series'] + '_x_' + perf_measure_results[additional_vars].agg('_x_'.join, axis=1)

            for col in perf_measure_results.columns:
                # TODO: generate_if_possible should be done elsewhere in a more abstract way
                perf_measure_results.loc[:, col] = to_numeric_if_possible(perf_measure_results[col])

            for series in perf_measure_results.loc[:, 'series'].unique():

                # TODO: this needs to account for repeats
                # TODO: This is way over complicated
                series_results = perf_measure_results.query(f'series == "{series}" and (fom_origin_type == "application" or fom_origin_type == "summary::mean")')

                series_min = perf_measure_results.query(f'series == "{series}" and fom_origin_type == "summary::min"')
                series_max = perf_measure_results.query(f'series == "{series}" and fom_origin_type == "summary::max"')

                selected = series_results.loc[:, [f'{scale_var}', 'fom_value']]

                # TODO: what is driving the need for a pivot here?
                # TODO: can we seperate out the data generation from the plotting?
                scale_pivot = series_results.pivot_table('fom_value', index=scale_var)

                # TODO: add way to enable (or remove)
                need_table = False

                if need_table:
                    fig, axs = plt.subplots(2,1)
                    ax = axs[0]
                else:
                    fig, ax = plt.subplots()

                # TODO: We interpret this as requesting speedup, which isn't striclty true
                # We need a more clear semantic for this
                if self.normalize:
                    self.normalize_data(scale_pivot, speedup=True)

                    scale_pivot = self.add_ideal_line(perf_measure_results, scale_pivot)

                    ax.plot(scale_pivot.index, 'normalized_fom_value', data=scale_pivot, marker='o')
                    ax.set_ylabel('Speedup')
                else:
                    scale_pivot = self.add_ideal_line(perf_measure_results, scale_pivot)
                    ax.plot(scale_pivot.index, 'fom_value', data=scale_pivot, marker='o')

                    # TODO: move out so it works for normalized too
                    if not series_min.empty:
                        #series_min.loc[:, 'fom_value'] = to_numeric_if_possible(series_min['fom_value'])
                        #series_max.loc[:, 'fom_value'] = to_numeric_if_possible(series_max['fom_value'])

                        # I re-index to scale_var/n_nodes for the main data so we need it here too
                        series_min = series_min.set_index(scale_var)
                        series_max = series_max.set_index(scale_var)


                        logger.debug('Adding fill lines for min and max')
                        print('Min')
                        print(series_min['fom_value'])
                        print('Max')
                        print(series_max['fom_value'])
                        print('Actual')
                        print(scale_pivot['fom_value'])

                        scale_pivot['fom_value_min'] = series_min['fom_value']
                        scale_pivot['fom_value_max'] = series_max['fom_value']

                        ax.fill_between(
                                scale_pivot.index,
                                'fom_value_min',
                                'fom_value_max',
                                data=scale_pivot,
                                alpha=0.2)

                    ymin, ymax = ax.get_ylim()
                    plt.ylim(0, ymax*1.1)

                    ax.set_ylabel(f'{perf_measure}')

                ax.plot(scale_pivot.index, 'ideal_perf_value', data=scale_pivot)

                plt.legend(loc="upper left")
                ax.set_xlabel(f'{scale_var}')

                # ax.set_xscale('log')
                ax.set_xticks(scale_pivot.index.unique().tolist())
                ax.set_title(f'Strong Scaling: {perf_measure} vs {scale_var} for {series}', wrap=True)
                #plt.tight_layout()

                if need_table:
                    table_ax = axs[1]
                    self.show_table(table_ax, scale_pivot)

                chart_filename = f'strong-scaling_{perf_measure}_vs_{scale_var}_{series}.png'
                self.write(fig, chart_filename)


class FomPlot(PlotGenerator):
    def generate_plot(self, results_df):
        super().generate_plot(results_df)
        # TODO: what is this for?
        # this one doesn't have a chart spec, it's just a flag
        # first divide results into series based on workload namespace
        # then iterate over each fom in each series and create 1 bar chart per fom
        # comparing fom_value (y) by experiment (x)
        pass


class ComparisonPlot(PlotGenerator):
    def generate_plot(self, results_df):
        super().generate_plot(results_df)

        for chart_spec in self.spec:
            # Break out input args into FOMs and dimensions
            foms = []
            dimensions = []

            for input_spec in chart_spec:
                if input_spec in results_df.loc[:, 'fom_name'].values:
                    foms.append(input_spec)
                else:
                    dimensions.append(input_spec)

            if not dimensions:
                dimensions.append('experiment_name')

            raw_results = results_df[results_df.loc[:, 'fom_name'].isin(foms)].copy()

            raw_results.loc[:, 'Figure of Merit'] = (raw_results.loc[:, 'fom_name'] +
                                              ' (' + raw_results.loc[:, 'fom_units'] + ')')

            raw_results['fom_value'] = to_numeric_if_possible(pd.to_numeric(raw_results['fom_value']))

            plot_col = 'fom_value'
            if self.normalize:
                self.normalize_data(raw_results)
                plot_col = "normalized_fom_value"

            compare_pivot = raw_results.pivot_table(plot_col, index=dimensions, columns='Figure of Merit')

            # Pivot table aggregates values by mean. Check if results were aggregated and label them
            # Raw results have FOMs by row, pivot by columns, so multiply the pivot rows x cols
            print(f'raw values = {len(raw_results)}  vs pivot values = {len(compare_pivot)} x {len(compare_pivot.columns)} ={len(compare_pivot) * len(compare_pivot.columns)}')

            # If all FOMs are either higher or lower is better, add it to chart title
            title_suffix = ''
            if len(raw_results.loc[:, 'better_direction'].unique()) == 1:
                if raw_results.loc[:, 'better_direction'].unique()[0] == 'HIGHER':
                    title_suffix = '(higher is better)'
                elif raw_results.loc[:, 'better_direction'].unique()[0] == 'LOWER':
                    title_suffix = '(lower is better)'


            ax = compare_pivot.plot(kind="bar")
            fig = ax.get_figure()

            ax.set_title(f'{" vs ".join(foms)} by {" and ".join(dimensions)} {title_suffix}', wrap=True)

            plt.tight_layout()

            chart_filename = f'{"_vs_".join(foms)}_by_{"_and_".join(dimensions)}.png'
            self.write(fig, chart_filename)


def get_reports_path():
    """Returns current directory of ramble-created reports"""
    path_in_config = ramble.config.get("config:report_dirs")
    if not path_in_config:
        logger.die("No config:report_dirs setting found in configuration. To add one,  "
                   "use command: ramble config add \"config:report_dirs:~/.ramble/reports\"")

    report_path = ramble.util.path.canonicalize_path(str(path_in_config))
    return report_path


def make_report(results_df, ws_name, args):
    dt = datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    report_dir_root = get_reports_path()

    report_name = f"{ws_name}.{dt}"
    report_dir_path = os.path.join(report_dir_root, report_name)
    fs.mkdirp(report_dir_path)
    pdf_path = os.path.join(report_dir_path, f'{report_name}.pdf')

    with PdfPages(pdf_path) as pdf_report:

       plot_factory = PlotFactory()
       plot_generators = plot_factory.create_plot_generators(args, report_dir_path, pdf_report)

       for plot in plot_generators:
           plot.generate_plot(results_df)

    if os.path.isfile(pdf_path):
        logger.msg("Report generated successfully. A PDF summary is available at:\n"
                   f"    {pdf_path}")
        logger.msg("Individual chart images are available at:\n"
                   f"    {report_dir_path}")
