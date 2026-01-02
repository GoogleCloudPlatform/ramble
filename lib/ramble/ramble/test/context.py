# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import unittest

from ramble.context import Context


class TestContext(unittest.TestCase):
    def test_to_workspace_config(self):
        context = Context()
        context.context_name = "test_experiment"
        context.variables = {"foo": "bar"}
        config = context.to_workspace_config("test_app", "test_workload")
        self.assertIn("ramble", config)
        self.assertIn("applications", config["ramble"])
        self.assertIn("test_app", config["ramble"]["applications"])
        self.assertIn("workloads", config["ramble"]["applications"]["test_app"])
        self.assertIn("test_workload", config["ramble"]["applications"]["test_app"]["workloads"])
        self.assertIn(
            "experiments",
            config["ramble"]["applications"]["test_app"]["workloads"]["test_workload"],
        )
        self.assertIn(
            "test_experiment",
            config["ramble"]["applications"]["test_app"]["workloads"]["test_workload"][
                "experiments"
            ],
        )
        self.assertIn(
            "variables",
            config["ramble"]["applications"]["test_app"]["workloads"]["test_workload"][
                "experiments"
            ]["test_experiment"],
        )
        self.assertEqual(
            config["ramble"]["applications"]["test_app"]["workloads"]["test_workload"][
                "experiments"
            ]["test_experiment"]["variables"],
            {"foo": "bar"},
        )

    def test_to_workspace_config_all_attributes(self):
        context = Context()
        context.context_name = "test_experiment"
        context.variables = {"a": "b"}
        context.variants = {"c": "d"}
        context.env_variables = {"e": "f"}
        context.internals = {"g": "h"}
        context.chained_experiments = ["i"]
        context.modifiers = ["j"]
        context.template = "k"
        context.exclude = ["l"]
        context.zips = ["m"]
        context.tables = ["n"]
        context.tags = ["o"]
        context.matrices = {"p": "q"}
        context.n_repeats = 1
        context.formatted_executables = {"r": "s"}
        context.success_criteria = "t"

        config = context.to_workspace_config("test_app", "test_workload")
        experiment_config = config["ramble"]["applications"]["test_app"]["workloads"][
            "test_workload"
        ]["experiments"]["test_experiment"]

        self.assertEqual(experiment_config["variables"], {"a": "b"})
        self.assertEqual(experiment_config["variants"], {"c": "d"})
        self.assertEqual(experiment_config["env_vars"], {"e": "f"})
        self.assertEqual(experiment_config["internals"], {"g": "h"})
        self.assertEqual(experiment_config["chained_experiments"], ["i"])
        self.assertEqual(experiment_config["modifiers"], ["j"])
        self.assertEqual(experiment_config["template"], "k")
        self.assertEqual(experiment_config["exclude"], ["l"])
        self.assertEqual(experiment_config["zips"], ["m"])
        self.assertEqual(experiment_config["tables"], ["n"])
        self.assertEqual(experiment_config["tags"], ["o"])
        self.assertEqual(experiment_config["matrices"], {"p": "q"})
        self.assertEqual(experiment_config["n_repeats"], 1)
        self.assertEqual(experiment_config["formatted_executables"], {"r": "s"})
        self.assertEqual(experiment_config["success_criteria"], "t")
