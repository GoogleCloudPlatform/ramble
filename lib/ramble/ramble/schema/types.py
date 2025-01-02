# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Base types for building schema files from"""

string_or_num_list = [{"type": "string"}, {"type": "number"}]

string_or_num = {"anyOf": string_or_num_list}

array_of_strings_or_nums = {"type": "array", "default": [], "items": string_or_num}

array_or_scalar_of_strings_or_nums = {
    "anyOf": [*string_or_num_list, {"type": "array", "default": [], "items": string_or_num}]
}
