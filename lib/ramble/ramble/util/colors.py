# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

config_color = '@*Y'
header_color = '@*b'
level1_color = '@*g'
level2_color = '@*r'
level3_color = '@*c'
level4_color = '@*m'
plain_format = '@.'


def level_func(level):
    if level <= 0:
        return section_title
    elif level == 1:
        return nested_1
    elif level == 2:
        return nested_2
    elif level == 3:
        return nested_3
    elif level >= 4:
        return nested_4


def config_title(s):
    return config_color + s + plain_format


def section_title(s):
    return header_color + s + plain_format


def nested_1(s):
    return level1_color + s + plain_format


def nested_2(s):
    return level2_color + s + plain_format


def nested_3(s):
    return level3_color + s + plain_format


def nested_4(s):
    return level4_color + s + plain_format
