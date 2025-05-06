# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the util/output_capture functions"""

from ramble.util import output_capture


def test_output_capture():
    mapper = output_capture.output_mapper()
    assert (
        mapper.generate_out_string("log.out", output_capture.OUTPUT_CAPTURE.STDOUT)
        == ' >> "log.out"'
    )
    assert (
        mapper.generate_out_string("log.out", output_capture.OUTPUT_CAPTURE.STDERR)
        == ' 2>> "log.out"'
    )
    assert (
        mapper.generate_out_string("log.out", output_capture.OUTPUT_CAPTURE.ALL)
        == ' >> "log.out" 2>&1'
    )
