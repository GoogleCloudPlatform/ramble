# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
from typing import Dict, List

import ramble.util.colors


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


class SoftwareSpec:

    def __init__(
        self,
        name: str,
        pkg_spec: str,
        prefix: str = "",
        compiler: str = None,
        compiler_spec: str = None,
        when: List[str] = None,
    ):
        self.name = name
        self.pkg_spec = pkg_spec
        self.prefix = prefix
        self.compiler = compiler
        self.compiler_spec = compiler_spec
        self.when = when.copy()

    def to_dict(self, prefix: str = None):
        prefix_base = prefix if prefix is not None else self.prefix
        prefix_str = f"{prefix_base}_" if prefix_base else ""

        attrs = ["pkg_spec", "compiler", "compiler_spec"]

        output = {}
        for attr in attrs:
            val = getattr(self, attr, None)
            if val is not None:
                output[f"{prefix_str}{attr}"] = val
        return output

    def config_opts(self):
        self_dict = self.to_dict()
        for key, val in self_dict.items():
            yield f"software:packages:{self.name}:{key}:{val}"

    def as_str(self, indent=0):
        base_indent = " " * indent
        indentation = " " * (indent + 4)
        self_dict = self.to_dict()
        color_name = ramble.util.colors.section_title(self.name)
        output = f"{base_indent}{color_name}:\n"
        for key, val in self_dict.items():
            color_key = ramble.util.colors.nested_1(key)
            escaped_val = val.replace("@", "@@")
            output += f"{indentation}{color_key}: {escaped_val}\n"
        return output

    def __str__(self):
        self_dict = self.to_dict(prefix="")
        self_dict["prefix"] = self.prefix
        return str(self_dict)

    def copy(self):
        return copy.deepcopy(self)

    def conflict_spec(self, test, skip_conflicting_when: bool = True):
        if skip_conflicting_when:
            new_when = set(getattr(self, "when", set()))
            test_when = set(getattr(test, "when", set()))

            if new_when != test_when:
                return False

        if self.prefix != test.prefix:
            return False

        for attr in ["pkg_spec", "compiler", "compiler_spec"]:
            new_val = getattr(self, attr, None)
            test_val = getattr(test, attr, None)
            if new_val != test_val:
                return True

        return False

    def conflict_dict(self, test_dict: Dict):
        self_dict = self.to_dict()
        for key, val in self_dict.items():
            if key in test_dict and val != test_dict[key]:
                return True
        return False
