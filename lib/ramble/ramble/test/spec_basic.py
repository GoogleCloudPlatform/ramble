# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the Spec class"""

from ramble.spec import Spec


class TestSpec:

    def test_spec_examples(self):
        app_name = "test_application"
        test_spec = Spec(app_name)

        assert test_spec.name == app_name

    def test_spec_copy(self):
        app_name = "copy_application"
        main_spec = Spec(app_name)
        copy_spec = main_spec.copy()

        assert main_spec.name == copy_spec.name
