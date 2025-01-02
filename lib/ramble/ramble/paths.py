# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Defines paths that are part of Ramble's directory structure.

Do not import other ``ramble`` modules here. This module is used
throughout Ramble and should bring in a minimal number of external
dependencies.
"""
import os
from llnl.util.filesystem import ancestor

#: This file lives in $prefix/lib/ramble/ramble/__file__
prefix = ancestor(__file__, 4)

#: synonym for prefix
ramble_root = prefix

#: bin directory in the ramble prefix
bin_path = os.path.join(prefix, "bin")

#: The ramble script itself
ramble_script = os.path.join(bin_path, "ramble")

#: The sbang script in the ramble installation
sbang_script = os.path.join(bin_path, "sbang")

# ramble directory hierarchy
lib_path = os.path.join(prefix, "lib", "ramble")
external_path = os.path.join(lib_path, "external")
build_env_path = os.path.join(lib_path, "env")
module_path = os.path.join(lib_path, "ramble")
command_path = os.path.join(module_path, "cmd")
test_path = os.path.join(module_path, "test")
var_path = os.path.join(prefix, "var", "ramble")
tests_path = os.path.join(var_path, "tests")
share_path = os.path.join(prefix, "share", "ramble")
repos_path = os.path.join(var_path, "repos")
application_types_path = os.path.join(module_path, "application_types")

# Paths to built-in Ramble repositories.
builtin_path = os.path.join(repos_path, "builtin")
mock_builtin_path = os.path.join(repos_path, "builtin.mock")

#: User configuration location
user_config_path = os.path.expanduser("~/.ramble")

opt_path = os.path.join(prefix, "opt")
etc_path = os.path.join(prefix, "etc")
system_etc_path = "/etc"
