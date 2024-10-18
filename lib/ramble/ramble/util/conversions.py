# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def list_str_to_list(in_str):
    """Convert a comma delimited list as a string into a python list

    Args:
        in_str (str): Input string, comma delimited list of values

    Returns:
        (list) Each value from input string is a separate entry in the list.

    """
    if "[" not in in_str and "]" not in in_str:
        return in_str

    temp = in_str.replace("[", "").replace("]", "")
    out_value = []
    for part in temp.split(","):
        if part[0] == " ":
            out_value.append(part[1:])
        else:
            out_value.append(part)
    return out_value
