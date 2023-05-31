# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Base types for building schema files from"""


class OUTPUT_CAPTURE:
    STDERR = "2>"
    STDOUT = ">>"
    ALL = "&>"
    DEFAULT = STDOUT


# FIXME: should this use the vector notation which type natively supports?
string_or_num = {
    'anyOf': [
        {'type': 'string'},
        {'type': 'number'}
    ]
}

array_of_strings_or_nums = {
    'type': 'array',
    'default': [],
    'items': string_or_num
}

array_or_scalar_of_strings_or_nums = {
    'anyOf': [
        {
            'type': 'array',
            'default': [],
            'items': string_or_num,
        },
        string_or_num
    ]
}
