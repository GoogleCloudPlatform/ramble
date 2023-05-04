# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.expander


def exp_dict():
    return {
        'application_name': 'foo',
        'workload_name': 'bar',
        'experiment_name': 'baz',
        'application_input_dir': '/workspace/inputs/foo',
        'workload_input_dir': '/workspace/inputs/foo/bar',
        'application_run_dir': '/workspace/experiments/foo',
        'workload_run_dir': '/workspace/experiments/foo/bar',
        'experiment_run_dir': '/workspace/experiments/foo/bar/baz',
        'env_name': 'spack_foo.bar',
        'n_ranks': '4',
        'processes_per_node': '2',
        'n_nodes': '2',
        'var1': '{var2}',
        'var2': '{var3}',
        'var3': '3',
    }


def test_expansions():
    expansion_vars = exp_dict()

    expander = ramble.expander.Expander(expansion_vars, None)

    assert expander.expand_var('{var1}') == '3'
    assert expander.expand_var('{var2}') == '3'
    assert expander.expand_var('{var3}') == '3'
    assert expander.expand_var('{application_name}') == 'foo'

    assert expander.expand_var('{n_nodes}') == '2'
    assert expander.expand_var('{processes_per_node}') == '2'
    assert expander.expand_var('{n_nodes}*{processes_per_node}') == '4'
    assert expander.expand_var('2**4') == '16'
    assert expander.expand_var('((((16-10+2)/4)**2)*4)') == '16.0'


def test_expansion_namespaces():
    expansion_vars = exp_dict()

    expander = ramble.expander.Expander(expansion_vars, None)

    assert expander.application_namespace == 'foo'
    assert expander.workload_namespace == 'foo.bar'
    assert expander.experiment_namespace == 'foo.bar.baz'
