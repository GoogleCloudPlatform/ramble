from typing import Any, Optional, Union

# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def list_str_to_list(in_str: str) -> Union[str, list]:
    """Convert a comma delimited list as a string into a python list

    Args:
        in_str (str): Input string, comma delimited list of values

    Returns:
        (list) Each value from input string is a separate entry in the list.

    """
    if "[" not in in_str and "]" not in in_str:
        return in_str

    temp = in_str.replace("[", "").replace("]", "")
    out_value = [strip_quotes(part) for part in temp.split(",")]
    return out_value


def strip_quotes(in_str: str) -> str:
    """Remove quotes from a string if present."""
    # Strip whitespace
    in_str = in_str.strip()
    if len(in_str) >= 2:
        if (in_str.startswith("'") and in_str.endswith("'")) or (
            in_str.startswith('"') and in_str.endswith('"')
        ):
            return in_str[1:-1]
    return in_str


def canonical_none(maybe_none: Any) -> Optional[Any]:
    """Convert a small set of "none-looking" inputs to None"""
    if maybe_none == "":
        return None
    if isinstance(maybe_none, str) and maybe_none.lower() == "none":
        return None
    return maybe_none


def convert_to_number(val: Any) -> Any:
    "Convert (in order of preference) to int, or float, or simply return itself"
    if not isinstance(val, str):
        return val
    try:
        f_val = float(val)
        if f_val.is_integer():
            return int(f_val)
        return f_val
    except ValueError:
        return val
