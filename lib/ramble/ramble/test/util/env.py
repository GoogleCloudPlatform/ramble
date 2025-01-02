# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the util/env functions"""

import ramble.util.env


def test_env_var_set_command_gen(mutable_mock_apps_repo):
    tests = {"var1": "val1", "var2": "val2"}

    answer = ["export var1=val1;", "export var2=val2;"]

    out_cmds, _ = ramble.util.env.Env.get_env_set_commands(tests, set())
    for cmd in answer:
        assert cmd in out_cmds


def test_env_var_append_command_gen(mutable_mock_apps_repo):
    tests = [
        {
            "var-separator": ",",
            "vars": {"var1": "val1", "var2": "val2"},
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
        'export path1="${path1}:path1";',
        'export path2="${path2}:path2";',
    ]

    out_cmds, _ = ramble.util.env.Env.get_env_append_commands(tests, set())
    for cmd in answer:
        assert cmd in out_cmds


def test_env_var_prepend_command_gen(mutable_mock_apps_repo):
    tests = [
        {"paths": {"path1": "path1", "path2": "path2"}},
        {"paths": {"path1": "path2", "path2": "path1"}},
    ]

    answer = ['export path1="path2:path1:${path1}";', 'export path2="path1:path2:${path2}";']

    out_cmds, _ = ramble.util.env.Env.get_env_prepend_commands(tests, set())
    for cmd in answer:
        assert cmd in out_cmds


def test_env_var_unset_command_gen(mutable_mock_apps_repo):
    tests = ["var1", "var2"]

    answer = ["unset var1;", "unset var2;"]

    out_cmds, _ = ramble.util.env.Env.get_env_unset_commands(tests, set())
    for cmd in answer:
        assert cmd in out_cmds
