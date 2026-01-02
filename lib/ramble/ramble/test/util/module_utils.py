# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import unittest
from unittest.mock import patch

from ramble.util.module_utils import import_module


class TestModuleUtils(unittest.TestCase):
    @patch("ramble.util.logger.logger.die")
    def test_import_non_existent_module(self, mock_die):
        mock_die.side_effect = SystemExit
        with self.assertRaises(SystemExit):
            import_module("non_existent_module")
        mock_die.assert_called_once_with(
            "`non_existent_module` was not found. Ensure all the packages in "
            "`requirements.txt` are installed."
        )
