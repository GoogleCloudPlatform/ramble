# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import shutil
import tempfile
import unittest
from unittest import mock

import ramble.workspace
from ramble.filters import Filters
from ramble.pipeline import PushDeploymentPipeline


class TestPushDeploymentPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = ramble.workspace.Workspace(self.test_dir)
        self.deployment_name = "test_deployment"
        self.deployment_path = os.path.join(
            self.workspace.root, "deployments", self.deployment_name
        )
        self.workspace.deployment = self.deployment_name

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_complete_copies_inventory_files(self):
        # Create dummy inventory files
        inventory_file = os.path.join(self.workspace.root, self.workspace.inventory_file_name)
        hash_file = os.path.join(self.workspace.root, self.workspace.hash_file_name)
        metadata_file = os.path.join(self.workspace.root, ramble.workspace.METADATA_FILE_NAME)

        with open(inventory_file, "w") as f:
            f.write("inventory")
        with open(hash_file, "w") as f:
            f.write("hash")
        with open(metadata_file, "w") as f:
            f.write("metadata")

        pipeline = PushDeploymentPipeline(
            self.workspace,
            filters=Filters([]),
            deployment_name=self.deployment_name,
            create_tar=False,
        )
        pipeline._deployment_files = lambda: []
        pipeline._construct_experiment_hashes = lambda: False
        with mock.patch("ramble.expander.Expander.expand_var", return_value=self.deployment_name):
            pipeline._execute()
        pipeline._complete()

        # Check if the files were copied
        self.assertTrue(
            os.path.exists(os.path.join(self.deployment_path, self.workspace.inventory_file_name))
        )
        self.assertTrue(
            os.path.exists(os.path.join(self.deployment_path, self.workspace.hash_file_name))
        )
        self.assertTrue(
            os.path.exists(os.path.join(self.deployment_path, ramble.workspace.METADATA_FILE_NAME))
        )
