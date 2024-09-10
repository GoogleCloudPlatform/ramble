# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import ramble.schema.util.import_util as import_util


def test_import_external_spack_schema(tmpdir, working_env):
    ramble_root = os.environ["RAMBLE_ROOT"]
    # fallback to internal spack when path not-exist
    os.environ["SPACK_ROOT"] = "/not-exist/"
    mod = import_util.import_external_spack_schema("spack.schema.concretizer")
    assert mod.__file__.startswith(ramble_root)

    # reads in external spack when available
    tmp_file = os.path.join(tmpdir, "lib", "spack", "spack", "schema", "concretizer.py")
    os.makedirs(os.path.dirname(tmp_file))
    with open(tmp_file, "a"):
        pass
    os.environ["SPACK_ROOT"] = str(tmpdir)
    mod = import_util.import_external_spack_schema("spack.schema.concretizer")
    assert mod.__file__.startswith(str(tmpdir))
