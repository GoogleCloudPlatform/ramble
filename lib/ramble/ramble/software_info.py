# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


class SoftwareInfo:
    """Represents information about a software build configuration (standard class)."""

    def __init__(
        self, name="", version="unknown", compiler="", compiler_version="", target="", variants=""
    ):
        """Initializes the BuildInfo object."""
        self.name = name
        self.version = version
        self.compiler = compiler
        self.compiler_version = compiler_version
        self.target = target
        self.variants = variants

    def to_version_text(self):
        return f"{self.name} @{self.version}"

    def to_dict(self):
        return self.__dict__
