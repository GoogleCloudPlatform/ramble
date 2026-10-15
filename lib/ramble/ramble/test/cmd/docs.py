# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from unittest.mock import patch

from ramble.main import RambleCommand


def test_docs_opens_browser():
    """Test that docs command opens the web browser."""
    docs = RambleCommand("docs")
    with patch("webbrowser.open") as mock_open:
        docs()
        mock_open.assert_called_once_with("https://ramble.readthedocs.io/")
