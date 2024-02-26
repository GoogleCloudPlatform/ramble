# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


class SuccessCriteria(BasicModifier):
    """Define a modifier with a success criteria"""
    name = "success-criteria"

    mode('test', description='This is a test mode')

    success_criteria('status', mode='string', match='.*Experiment status: SUCCESS', file='{log_file}')

    variable_modification('experiment_status', modification='Experiment status: SUCCESS', method='set', mode='test')

    register_builtin('echo_status', required=True)

    def echo_status(self):
        return ['echo "Experiment status: {experiment_status}" >> {log_file}']
