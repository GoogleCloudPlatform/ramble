# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import importlib
import importlib.util
import os


# TODO: This does not work with nested imports
def import_external_spack_schema(fullname):
    """Import a single schema source from the external Spack, if available"""
    ext_spack_root = os.environ.get("SPACK_ROOT")
    module = None
    if ext_spack_root is not None:
        _, _, leaf = fullname.rpartition(".")
        src_path = os.path.join(ext_spack_root, "lib", "spack", "spack", "schema", leaf + ".py")
        if os.path.exists(src_path):
            spec = importlib.util.spec_from_file_location(fullname, src_path)
            module = importlib.util.module_from_spec(spec)
            if module is not None:
                spec.loader.exec_module(module)
    if module is None:
        module = importlib.import_module(fullname)
    return module
