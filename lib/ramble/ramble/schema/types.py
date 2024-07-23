# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Base types for building schema files from"""

from enum import Enum


class OUTPUT_CAPTURE(Enum):
    STDOUT = 0
    STDERR = 1
    ALL = 2
    DEFAULT = 2


class output_mapper:
    def __init__(self):
        self.map = {
            OUTPUT_CAPTURE.STDOUT: ">>",
            OUTPUT_CAPTURE.STDERR: "2>>",
            OUTPUT_CAPTURE.ALL: ">>",
        }
        self.SUFFIX = "2>&1"

    def generate_out_string(self, out_log, output_operator):
        redirect_str = f' {self.map.get(output_operator, output_operator)} "{out_log}"'
        if output_operator is OUTPUT_CAPTURE.ALL:
            redirect_str += f" {self.SUFFIX}"

        return redirect_str


string_or_num_list = [{"type": "string"}, {"type": "number"}]

string_or_num = {"anyOf": string_or_num_list}

array_of_strings_or_nums = {"type": "array", "default": [], "items": string_or_num}

array_or_scalar_of_strings_or_nums = {
    "anyOf": [*string_or_num_list, {"type": "array", "default": [], "items": string_or_num}]
}
