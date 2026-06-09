# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble import main
from ramble.cmd import license

license_cmd = main.RambleCommand("license")


def test_verify_empty():
    out = license_cmd("verify", "--modified")
    assert "No license issues found" in out


def test_verify_with_error(tmpdir):
    wrong_lic_header = """
# Copyright 2020-2023 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""
    with tmpdir.as_cwd():
        # Mimic the bin/
        os.mkdir("bin")
        file_with_lic = tmpdir / "bin" / "ramble"
        with open(file_with_lic, "w", encoding="utf-8") as f:
            f.write(wrong_lic_header)
        out = license_cmd("verify", "--root", str(tmpdir), fail_on_error=False)
        assert "the license does not match the expected format" in out

        new_header = wrong_lic_header.replace("2020-2023", license.strict_date_range)
        with open(file_with_lic, "w", encoding="utf-8") as f:
            f.write(new_header)
        out = license_cmd("verify", "--root", str(tmpdir))
        assert "No license issues found" in out
