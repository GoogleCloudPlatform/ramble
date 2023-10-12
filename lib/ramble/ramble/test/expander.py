# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

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
        'decimal.06.var': 'foo',
    }


@pytest.mark.parametrize(
    'input,output',
    [
        ('{var1}', '3'),
        ('{var2}', '3'),
        ('{var3}', '3'),
        ('{application_name}', 'foo'),
        ('{n_nodes}', '2'),
        ('{processes_per_node}', '2'),
        ('{n_nodes}*{processes_per_node}', '4'),
        ('2**4', '16'),
        ('{((((16-10+2)/4)**2)*4)}', '16.0'),
        ('gromacs +blas', 'gromacs +blas'),
        ('range(0, 5)', '[0, 1, 2, 3, 4]'),
        ('{decimal.06.var}', 'foo'),
        ('{}', '{}'),
        ('{{n_ranks}+2}', '6'),
        ('{{n_ranks}*{var{processes_per_node}}:05d}', '00012'),
        ('{{n_ranks}-1}', '3'),
    ]
)
def test_expansions(input, output):
    expansion_vars = exp_dict()

    expander = ramble.expander.Expander(expansion_vars, None)

    assert expander.expand_var(input) == output


@pytest.mark.parametrize(
    'input,output',
    [
        ('application_name', 'foo'),
        ('workload_name', 'bar'),
        ('experiment_name', 'baz'),
        ('var1', '3'),
        ('var2', '3'),
        ('var3', '3'),
    ]
)
def test_expand_var_name(input, output):
    expansion_vars = exp_dict()

    expander = ramble.expander.Expander(expansion_vars, None)

    assert expander.expand_var_name(input) == output


def test_expansion_namespaces():
    expansion_vars = exp_dict()

    expander = ramble.expander.Expander(expansion_vars, None)

    assert expander.application_namespace == 'foo'
    assert expander.workload_namespace == 'foo.bar'
    assert expander.experiment_namespace == 'foo.bar.baz'
