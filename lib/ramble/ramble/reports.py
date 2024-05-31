# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
import itertools

import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


import ramble.experimental.uploader
import ramble.cmd.workspace
import ramble.pipeline
import ramble.filters
from  ramble.util.logger import logger



def is_numeric(series):
    """Check if a pandas series contains only numeric values.
    """
    try:
        pd.to_numeric(series)
        return True
    except (ValueError, TypeError):
        return False


def prepare_data(results: dict) -> pd.DataFrame:
    """Creates a Pandas DataFrame from the results dictionary to use for reports.
    """

    unnest_context = []
    # first unnest dictionaries
    for exp in results['experiments']:
        if exp['RAMBLE_STATUS'] == 'SUCCESS':
            for context in exp['CONTEXTS']:
                for fom in context['foms']:
                    # Expand to one row per FOM per context w/ a copy of the experiment vars and metadata
                    exp_copy = copy.deepcopy(exp)

                    # Remove context dict and add the current FOM values
                    exp_copy.pop('CONTEXTS')
                    exp_copy['context'] = context['display_name']
                    exp_copy['fom_name'] = fom['name']
                    exp_copy['fom_value'] = fom['value']
                    exp_copy['fom_units'] = fom['units']
                    exp_copy['fom_origin'] = fom['origin']
                    exp_copy['fom_origin_type'] = fom['origin_type']

                    # Flatten final vars dict and drop raw vars dict
                    exp_copy.pop('RAMBLE_VARIABLES')
                    exp_copy.pop('RAMBLE_RAW_VARIABLES')

                    # Ignore vars that aren't needed for analysis, mainly paths and commands
                    vars_to_ignore = [
                        'log_dir',
                        'batch_submit',
                        'application_run_dir',
                        'application_input_dir',
                        'workload_run_dir',
                        'workload_input_dir',
                        'license_input_dir',
                        'experiment_run_dir',
                        'env_path',
                        'log_file',
                        'input_path',
                        'command',
                        'execute_experiment'
                    ]
                    for key, value in exp['RAMBLE_VARIABLES'].items():
                        if key in vars_to_ignore:
                            continue
                        exp_copy[key] = value

                    unnest_context.append(exp_copy)
        else:  # exclude failed experiments from dataset
            continue

    results_df = pd.DataFrame.from_dict(unnest_context)

    # Convert numeric columns to numeric
    # TODO(dpomeroy): need to fix this for fom_values column
    # to handle case when there are both numeric and non-numeric FOMs
    for col in results_df.columns:
        if is_numeric(results_df[col]):
            results_df.loc[:, col] = pd.to_numeric(results_df[col])

    pd.DataFrame.to_json(results_df, 'results.json')

    return results_df


def make_report(ws, args):
    # analyze_pipeline = ramble.pipeline.pipelines.analyze
    # pipeline_cls = ramble.pipeline.pipeline_class(analyze_pipeline)

    # filters = ramble.filters.Filters(
    #     phase_filters='*'
    # )
    # pipeline = pipeline_cls(ws, filters)
    # pipeline.run()

    # results_df = prepare_data(ws.results)

    import json
    with open('/usr/local/google/home/dpomeroy/VSCode/ramble/var/ramble/workspaces/ansys-mech-archive/results.latest.json', 'r') as f:
        results = json.load(f)

    results_df = prepare_data(results)

    # pd.DataFrame.to_csv(results_df, 'results.csv')

    # import pprint
    # pprint.pprint(ws.results)
    # print(args)
    # print(args.scaling)

    # print(results_df.dtypes)

    with PdfPages('report.pdf') as pdf:

        if args.scaling:
            scaling = list(itertools.chain.from_iterable(args.scaling))

            if len(scaling) < 2:
                logger.die('Scaling plot requires two arguments: '
                        'performance metric and scaling metric')

            for col in scaling:
                if col not in results_df.columns and col not in results_df.loc[: ,'fom_name'].values:
                    logger.die(f'{col} was not found in the results data.')

            perf_measure, scale_var, *additional_vars = scaling

            # FOMs are by row, so select only rows with the perf_measure FOM
            perf_results = results_df.query(f'fom_name == "{perf_measure}"')

            perf_results.loc[:, 'series'] = perf_results.loc[:, 'workload_namespace']
            if additional_vars:
                for var in additional_vars:
                    perf_results.loc[:, 'series'] = perf_results.loc[:, 'series'] + '_' + perf_results.loc[:, var].astype(str)

            for series in perf_results['series'].unique():
                fig, ax = plt.subplots()
                
                ax.plot(f'{scale_var}', 'fom_value', data=perf_results.query(f'series == "{series}"'), marker='o')
                ax.set_xlabel(f'{scale_var}')
                # ax.set_xticks(perf_results[f'{scale_var}'].unique())
                ax.set_ylabel(f'{perf_measure}')
                ax.set_title(f'Scaling Chart for {series}')
                
                # fig =  (perf_results.query(f'series == "{series}"'), x=f'{scale_var}', y='fom_value')
                    # fig.update_layout(title=f'Scaling Chart for {data["perf_name"]} vs {data["scale_name"]}',
                    #                     xaxis_title=data['scale_name'],
                    #                     yaxis_title=data['perf_name'])
                #fig.show()
                pdf.savefig(fig)
                plt.close(fig)
            
            
            # pd.DataFrame.to_csv(results_df, 'results.csv')
