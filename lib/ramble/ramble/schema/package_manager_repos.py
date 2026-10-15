# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for package_manager_repos.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/package_manager_repos.py
   :lines: 13-
"""

from ramble.schema.repo_schema import make_repo_properties, make_repo_schema

section_name = "package_manager_repos"

#: Properties for inclusion in other schemas
properties = make_repo_properties(section_name)

#: Full schema with metadata
schema = make_repo_schema(section_name)
