# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the util/env functions"""

import ramble.util.env
from ramble.expander import Expander


def test_env_var_set_command_gen(mutable_mock_apps_repo):
    tests = {"var1": "val1", "var2": "val2", "{test_exp}": "bar"}

    answer = ["export var1=val1;", "export var2=val2;", "export foo=bar;"]

    exp_vars = {"test_exp": "foo"}

    expander = Expander(exp_vars, None)

    out_cmds, _ = ramble.util.env.action_funcs["set"](tests, expander, set())
    for cmd in answer:
        assert cmd in out_cmds


def test_env_var_append_command_gen(mutable_mock_apps_repo):
    tests = [
        {
            "var-separator": ",",
            "vars": {"var1": "val1", "var2": "val2", "{test_exp}": "bar"},
            "paths": {"path1": "path1", "path2": "path2"},
        },
        {
            "var-separator": ",",
            "vars": {"var1": "val2", "var2": "val1"},
        },
    ]

    answer = [
        'export var1="${var1},val1,val2";',
        'export var2="${var2},val2,val1";',
        'export foo="${foo},bar";',
        'export path1="${path1}:path1";',
        'export path2="${path2}:path2";',
    ]

    exp_vars = {"test_exp": "foo"}
    expander = Expander(exp_vars, None)

    out_cmds, _ = ramble.util.env.action_funcs["append"](tests, expander, set())
    for cmd in answer:
        assert cmd in out_cmds


def test_env_var_prepend_command_gen(mutable_mock_apps_repo):
    tests = [
        {"paths": {"path1": "path1", "path2": "path2", "{test_exp}": "bar"}},
        {"paths": {"path1": "path2", "path2": "path1", "{test_exp}": "bar"}},
    ]

    answer = [
        'export path1="path2:path1:${path1}";',
        'export path2="path1:path2:${path2}";',
        'export foo="bar:bar:${foo}";',
    ]

    exp_vars = {"test_exp": "foo"}

    expander = Expander(exp_vars, None)

    out_cmds, _ = ramble.util.env.action_funcs["prepend"](tests, expander, set())
    for cmd in answer:
        assert cmd in out_cmds


def test_env_var_unset_command_gen(mutable_mock_apps_repo):
    tests = ["var1", "var2", "{test_exp}"]

    answer = ["unset var1;", "unset var2;", "unset foo;"]

    exp_vars = {"test_exp": "foo"}

    expander = Expander(exp_vars, None)

    out_cmds, _ = ramble.util.env.action_funcs["unset"](tests, expander, set())
    for cmd in answer:
        assert cmd in out_cmds
