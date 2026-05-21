# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import tempfile


class MockPackageInfo:
    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data

    def to_version_text(self):
        return f"{self.data.get('name', 'unknown')} @{self.data.get('version', 'unknown')}"

    def __getitem__(self, key):
        return self.data[key]


class MockSpackRunner:
    def __init__(self):
        self.env_path = None
        self.concretized = False
        self.dry_run = False

    def set_env(self, env_path, require_exists=True):
        self.env_path = env_path

    def set_dry_run(self, dry_run):
        self.dry_run = dry_run

    def set_compiler_config_dir(self, path):
        pass

    def activate(self):
        pass

    def deactivate(self):
        pass

    def concretize(self):
        if not self.env_path:
            return

        # write dummy spack.yaml and spack.lock
        spack_yaml = os.path.join(self.env_path, "spack.yaml")
        with open(spack_yaml, "w") as f:
            f.write("specs:\n  - zlib\n")

        spack_lock = os.path.join(self.env_path, "spack.lock")
        with open(spack_lock, "w") as f:
            f.write('{"roots": [{"spec":"zlib"}]}')

        self.concretized = True

    def package_provenance(self):
        return [
            MockPackageInfo(
                {
                    "name": "zlib",
                    "version": "1.2.11",
                    "compiler": "gcc",
                    "compiler_version": "9.3.0",
                    "target": "x86_64",
                    "variants": "none",
                }
            )
        ]

    def get_version(self):
        return "0.0.0"

    def generate_source_command(self):
        return ["echo 'source spack'"]

    def generate_activate_command(self):
        return ["echo 'activate spack'"]

    def generate_deactivate_command(self):
        return ["echo 'deactivate spack'"]

    def configure_env(self, env_path):
        pass

    def add_config_file(self, config_file):
        pass

    def inventory_hash(self):
        return "dummy_hash"

    def package_definitions(self):
        return []

    def create_stage_env(self):
        tmp_path = tempfile.mkdtemp()
        return tmp_path

    def migrate_stage_env(self, stage_env_path: str, ws_env_path: str):
        pass

    def create_env(self, env_path):
        if not os.path.exists(env_path):
            os.makedirs(env_path)

    def add_config(self, config):
        pass

    def apply_configs(self, stage_path=None):
        pass

    def add_include_file(self, path):
        pass

    def copy_from_external_env(self, env):
        pass

    def add_spec(self, spec):
        pass

    def generate_env_file(self):
        pass

    def added_packages(self):
        return []

    def install(self):
        pass

    def get_package_path(self, spec):
        return "zlib", "/path/to/zlib"
