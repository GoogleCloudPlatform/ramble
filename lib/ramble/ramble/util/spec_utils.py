# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def specs_equiv(spec1, spec2):
    all_keys = set()
    for key in spec1.keys():
        if spec1[key] is not None:
            all_keys.add(key)
    for key in spec2.keys():
        if spec2[key] is not None:
            all_keys.add(key)

    if "application_name" in all_keys:
        all_keys.remove("application_name")

    if "spec_type" in all_keys:
        all_keys.remove("spec_type")

    if "package_manager" in all_keys:
        all_keys.remove("package_manager")

    if "when" in all_keys:
        all_keys.remove("when")

    for key in all_keys:
        if key not in spec1:
            return False
        if key not in spec2:
            return False
        if spec1[key] != spec2[key]:
            return False

    return True
