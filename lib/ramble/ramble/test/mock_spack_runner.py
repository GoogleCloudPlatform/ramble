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
    def __init__(self, **kwargs):
        self.env = kwargs.get("env", None)
        self.env_path = None
        self.concretized = False
        self.dry_run = False
        self.env_contents = []

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
        os.makedirs(self.env_path, exist_ok=True)
        spack_yaml = os.path.join(self.env_path, "spack.yaml")
        with open(spack_yaml, "w", encoding="utf-8") as f:
            f.write("specs:\n  - zlib\n")

        spack_lock = os.path.join(self.env_path, "spack.lock")
        with open(spack_lock, "w", encoding="utf-8") as f:
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

    def generate_activate_command(self, shell="bash"):
        return ["spack env activate %s" % self.env_path]

    def configure_env(self, env_path):
        self.env_path = env_path

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
        import shutil

        if stage_env_path and os.path.exists(stage_env_path):
            os.makedirs(ws_env_path, exist_ok=True)
            for item in os.listdir(stage_env_path):
                s = os.path.join(stage_env_path, item)
                d = os.path.join(ws_env_path, item)
                if os.path.isdir(s):
                    self.migrate_stage_env(s, d)
                else:
                    shutil.copy2(s, d)

    def create_env(self, env_path):
        if not os.path.exists(env_path):
            os.makedirs(env_path)
        self.env_path = env_path

    def apply_configs(self, stage_path=None):
        pass

    def add_include_file(self, path):
        pass

    def copy_from_external_env(self, env):
        pass

    def add_spec(self, spec):
        if spec not in self.env_contents:
            self.env_contents.append(spec)

    def generate_env_file(self):
        pass

    def added_packages(self):
        import re

        package_name_regex = re.compile(r"[\s-]*(?P<package_name>[\w][\w-]+).*")
        pkg_names = []
        for pkg in self.env_contents:
            match = package_name_regex.match(pkg)
            if match:
                pkg_names.append(match.group("package_name"))
        return pkg_names

    def install(self):
        pass

    def get_package_path(self, spec):
        return "zlib", "/path/to/zlib"

    def push_to_spack_cache(self, spack_cache_path, compiler_specs):
        pass

    def install_compiler(self, pkg_spec, compiler_spec):
        pass

    def get_spack_python(self):
        return None
