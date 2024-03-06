# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


class TestMod(BasicModifier):
    """Define a test modifier

    This modifier is just a test of various aspects of the modifier language.
    """
    name = "test-mod"

    tags('test')

    mode('test', description='This is a test mode')

    variable_modification('mpi_command', 'echo "prefix_mpi_command" >> {log_file}; ', method='prepend', modes=['test'])

    variable_modification('analysis_log', '{experiment_run_dir}/test_analysis.log', method='set', modes=['test'])

    software_spec('analysis_spec', spack_spec='analysis_pkg@1.1', compiler='gcc')

    fom_regex = r'(?P<context>fom_context)(?P<fom>.*)'

    figure_of_merit('test_mod_fom', fom_regex=fom_regex, group_name='fom',
                    units='', log_file='{analysis_log}', contexts=['test_mod_context'])

    figure_of_merit('shared_context_fom', fom_regex=fom_regex, group_name='fom',
                    units='', log_file='{analysis_log}', contexts=['test_shared_context'])

    figure_of_merit_context('test_mod_context', regex=fom_regex, output_format='{context}')

    figure_of_merit_context('test_shared_context', regex=fom_regex, output_format='matched_shared_context')

    register_builtin('test_builtin', required=True, injection_method='append')

    test_attr = 'test_value'

    def test_builtin(self):
        return ['echo "fom_contextFOM_GOES_HERE" >> {analysis_log}',
                f'echo "{self.test_attr}"' + ' >> {analysis_log}']
