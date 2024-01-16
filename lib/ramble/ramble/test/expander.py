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
        'size': '"0000.96"'  # Escaped as a string
    }


@pytest.mark.parametrize(
    'input,output,no_expand_vars',
    [
        ('{var1}', '3', set()),
        ('{var2}', '3', set()),
        ('{var3}', '3', set()),
        ('{application_name}', 'foo', set()),
        ('{n_nodes}', '2', set()),
        ('{processes_per_node}', '2', set()),
        ('{n_nodes}*{processes_per_node}', '4', set()),
        ('2**4', '16', set()),
        ('{((((16-10+2)/4)**2)*4)}', '16.0', set()),
        ('gromacs +blas', 'gromacs +blas', set()),
        ('range(0, 5)', '[0, 1, 2, 3, 4]', set()),
        ('{decimal.06.var}', 'foo', set()),
        ('{}', '{}', set()),
        ('{{n_ranks}+2}', '6', set()),
        ('{{n_ranks}*{var{processes_per_node}}:05d}', '00012', set()),
        ('{{n_ranks}-1}', '3', set()),
        ('{{{n_ranks}/2}:0.0f}', '2', set()),
        ('{size}', '0000.96', set(['size'])),
    ]
)
def test_expansions(input, output, no_expand_vars):
    expansion_vars = exp_dict()

    expander = ramble.expander.Expander(expansion_vars, None, no_expand_vars=no_expand_vars)

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
