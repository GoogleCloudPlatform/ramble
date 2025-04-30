# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def specs_conflict(new, existing, prefix="", skip_conflicting_when=False):
    # Short circuit check if when clauses conflict
    # (so specs should not be applied at the same time)
    # Used for printing conflicting software specs.
    if skip_conflicting_when:
        new_when = set(new["when"]) if "when" in new else None
        existing_when = set(existing["when"]) if "when" in existing else None

        if new_when != existing_when:
            return False

    prefixed_keys = {}
    for key in new.keys():
        if new[key] is not None:
            prefixed_keys[key] = f"{prefix}{key}"

    for in_key, out_key in prefixed_keys.items():
        if out_key in existing and new[in_key] != existing[out_key]:
            return True
    return False
