# Copyright 2022-2024 Google LLC
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
        'size': '"0000.96"',  # Escaped as a string
        'test_mask': '"0x0"',
    }


@pytest.mark.parametrize(
    'input,output,no_expand_vars,passes',
    [
        ('{var1}', '3', set(), 1),
        ('{var2}', '3', set(), 1),
        ('{var3}', '3', set(), 1),
        ('{application_name}', 'foo', set(), 1),
        ('{n_nodes}', '2', set(), 1),
        ('{processes_per_node}', '2', set(), 1),
        ('{n_nodes}*{processes_per_node}', '4', set(), 1),
        ('2**4', '16', set(), 1),
        ('{((((16-10+2)/4)**2)*4)}', '16.0', set(), 1),
        ('gromacs +blas', 'gromacs +blas', set(), 1),
        ('range(0, 5)', '[0, 1, 2, 3, 4]', set(), 1),
        ('{decimal.06.var}', 'foo', set(), 1),
        ('{}', '{}', set(), 1),
        ('{{n_ranks}+2}', '6', set(), 1),
        ('{{n_ranks}*{var{processes_per_node}}:05d}', '00012', set(), 1),
        ('{{n_ranks}-1}', '3', set(), 1),
        ('{{{n_ranks}/2}:0.0f}', '2', set(), 1),
        ('{size}', '0000.96', set(['size']), 1),
        ('CPU(s)', 'CPU(s)', set(), 1),
        ('str(1.5)', '1.5', set(), 1),
        ('int(1.5)', '1', set(), 1),
        ('float(1.5)', '1.5', set(), 1),
        ('ceil(0.6)', '1', set(), 1),
        ('floor(0.6)', '0', set(), 1),
        ('max(1, 5)', '5', set(), 1),
        ('min(1, 5)', '1', set(), 1),
        ('simplify_str("a.b_c")', 'a-b-c', set(), 1),
        (r'\{experiment_name\}', '{experiment_name}', set(), 1),
        (r'\{experiment_name\}', 'baz', set(), 2),
        (r'{\{experiment_name\}}', '{{experiment_name}}', set(), 1),
        (r'\\{experiment_name\\}', r'\{experiment_name\}', set(), 1),
        (r'\\{experiment_name\\}', '{experiment_name}', set(), 2),
        (r'\\{experiment_name\\}', 'baz', set(), 3),
        ('"2.1.1" in ["2.1.1", "3.1.1", "4.2.1"]', 'True', set(), 1),
        ('"2.1.2" in ["2.1.1", "3.1.1", "4.2.1"]', 'False', set(), 1),
        ('{test_mask}', '0x0', set(['test_mask']), 1),
    ]
)
def test_expansions(input, output, no_expand_vars, passes):
    expansion_vars = exp_dict()

    expander = ramble.expander.Expander(expansion_vars, None, no_expand_vars=no_expand_vars)

    step_input = input
    for _ in range(0, passes):
        step_input = expander.expand_var(step_input)
    final_output = step_input

    assert final_output == output


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
