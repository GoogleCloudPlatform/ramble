# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import unittest
from unittest.mock import MagicMock, patch

from ramble.results_table import ResultsTable


class TestContextColumns(unittest.TestCase):
    def test_context_column_discovery(self):
        conf_dict = {
            "name": "table",
            "columns": [{"name": "Static", "expression": "const"}],
            "autocolumns": [
                {"name": "Latency {bytes}", "context_name": "latency-*", "figure_of_merit": "Avg"}
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True

        # Mock expander.expand_var to handle {bytes} and others
        def side_effect(var, extra_vars=None):
            if extra_vars:
                # Basic template expansion for test
                res = var
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
                return res
            return var

        app_inst.expander.expand_var.side_effect = side_effect

        app_inst.result.contexts = [
            {
                "name": "latency-1",
                "context_def_name": "latency-bytes",
                "context_vars": {"bytes": "1"},
                "foms": [{"name": "Avg", "value": 1.0, "origin_type": "application"}],
            },
            {
                "name": "latency-2",
                "context_def_name": "latency-bytes",
                "context_vars": {"bytes": "2"},
                "foms": [{"name": "Avg", "value": 2.0, "origin_type": "application"}],
            },
        ]

        # Test row extraction and discovery
        table.extract_row(app_inst)

        self.assertEqual(table._num_rows, 1)
        self.assertIn("Static", table._data)
        self.assertIn("Latency 1", table._data)
        self.assertIn("Latency 2", table._data)
        self.assertEqual(table._data["Latency 1"], [1.0])
        self.assertEqual(table._data["Latency 2"], [2.0])

    def test_context_column_fom_globbing(self):
        conf_dict = {
            "name": "table",
            "autocolumns": [
                {"name": "{fom_name} {size}", "context_name": "ctx", "figure_of_merit": "*"}
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True

        def side_effect(var, extra_vars=None):
            if extra_vars:
                res = var
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
                return res
            return var

        app_inst.expander.expand_var.side_effect = side_effect

        app_inst.result.contexts = [
            {
                "name": "formatted-ctx",
                "context_def_name": "ctx",
                "context_vars": {"size": "large"},
                "foms": [
                    {"name": "FOM1", "value": 10, "origin_type": "application"},
                    {"name": "FOM2", "value": 20, "origin_type": "application"},
                ],
            }
        ]

        table.extract_row(app_inst)

        self.assertIn("FOM1 large", table._data)
        self.assertIn("FOM2 large", table._data)
        self.assertEqual(table._data["FOM1 large"], [10])
        self.assertEqual(table._data["FOM2 large"], [20])

    def test_context_column_ambiguous_names(self):
        # Test that contexts with same name but different metadata are handled correctly
        conf_dict = {
            "name": "table",
            "autocolumns": [{"name": "Col {val}", "context_name": "ctx*", "figure_of_merit": "F"}],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True

        def side_effect(var, extra_vars=None):
            if extra_vars:
                res = var
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
                return res
            return var

        app_inst.expander.expand_var.side_effect = side_effect

        app_inst.result.contexts = [
            {
                "name": "Ctx",
                "context_def_name": "ctx1",
                "context_vars": {"val": "1"},
                "foms": [{"name": "F", "value": 100, "origin_type": "application"}],
            },
            {
                "name": "Ctx",
                "context_def_name": "ctx2",
                "context_vars": {"val": "2"},
                "foms": [{"name": "F", "value": 200, "origin_type": "application"}],
            },
        ]

        table.extract_row(app_inst)

        self.assertIn("Col 1", table._data)
        self.assertIn("Col 2", table._data)
        self.assertEqual(table._data["Col 1"], [100])
        self.assertEqual(table._data["Col 2"], [200])

    def test_context_column_sorting(self):
        conf_dict = {
            "name": "table",
            "autocolumns": [
                {
                    "name": "BW {size}",
                    "context_name": "bw-*",
                    "figure_of_merit": "Bandwidth",
                    "sort_by": ["size"],
                }
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True

        def side_effect(var, extra_vars=None):
            if extra_vars:
                res = var
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
                return res
            return var

        app_inst.expander.expand_var.side_effect = side_effect

        # Add rows in non-sorted order
        app_inst.result.contexts = [
            {
                "name": "bw-1024",
                "context_def_name": "bw-bytes",
                "context_vars": {"size": "1024"},
                "foms": [{"name": "Bandwidth", "value": 1000, "origin_type": "application"}],
            },
            {
                "name": "bw-64",
                "context_def_name": "bw-bytes",
                "context_vars": {"size": "64"},
                "foms": [{"name": "Bandwidth", "value": 50, "origin_type": "application"}],
            },
            {
                "name": "bw-256",
                "context_def_name": "bw-bytes",
                "context_vars": {"size": "256"},
                "foms": [{"name": "Bandwidth", "value": 200, "origin_type": "application"}],
            },
        ]

        table.extract_row(app_inst)

        # Columns should be sorted by size: 64, 256, 1024
        col_names = list(table._data.keys())
        expected_order = ["BW 64", "BW 256", "BW 1024"]
        self.assertEqual(col_names, expected_order)

    def test_context_column_manual_conflict(self):
        conf_dict = {
            "name": "table",
            "columns": [{"name": "Conflict", "expression": "ManualValue"}],
            "autocolumns": [
                {"name": "Conflict", "context_name": "ctx", "figure_of_merit": "FomValue"}
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True

        def side_effect(var, extra_vars=None):
            if var == "ManualValue":
                return "Manual"
            if extra_vars:
                res = var
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
                return res
            return var

        app_inst.expander.expand_var.side_effect = side_effect

        app_inst.result.contexts = [
            {
                "name": "ctx",
                "context_def_name": "ctx",
                "context_vars": {},
                "foms": [{"name": "FomValue", "value": 100, "origin_type": "application"}],
            }
        ]

        table.extract_row(app_inst)

        # Manual column should win
        self.assertIn("Conflict", table._data)
        self.assertEqual(table._data["Conflict"], ["Manual"])

    def test_context_column_where_clause(self):
        conf_dict = {
            "name": "table",
            "autocolumns": [
                {
                    "name": "Incl {val}",
                    "context_name": "ctx",
                    "figure_of_merit": "F",
                    "where": ["{n_nodes} > 1"],
                }
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()

        def side_effect(var, extra_vars=None):
            res = var.replace("{n_nodes}", "2")
            if extra_vars:
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
            return res

        app_inst.expander.expand_var.side_effect = side_effect

        def eval_predicate(expr):
            # Simple eval for testing
            if ">" in expr:
                # Expand before eval
                expanded = app_inst.expander.expand_var(expr)
                parts = expanded.split(">")
                return float(parts[0].strip()) > float(parts[1].strip())
            return True

        app_inst.expander.evaluate_predicate.side_effect = eval_predicate

        app_inst.result.contexts = [
            {
                "name": "ctx",
                "context_def_name": "ctx",
                "context_vars": {"val": "15"},
                "foms": [{"name": "F", "value": 150, "origin_type": "application"}],
            },
        ]

        table.extract_row(app_inst)

        self.assertIn("Incl 15", table._data)
        self.assertEqual(table._data["Incl 15"], [150])

        # Test with where clause failing
        conf_dict["autocolumns"][0]["where"] = ["{n_nodes} > 4"]
        table2 = ResultsTable(conf_dict)
        table2.extract_row(app_inst)
        self.assertEqual(table2._data, {})

    def test_context_column_mixed_sorting(self):
        conf_dict = {
            "name": "table",
            "autocolumns": [
                {
                    "name": "{a}-{b}",
                    "context_name": "ctx",
                    "figure_of_merit": "F",
                    "sort_by": ["a", "b"],
                }
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True

        def side_effect(var, extra_vars=None):
            if extra_vars:
                res = var
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
                return res
            return var

        app_inst.expander.expand_var.side_effect = side_effect

        app_inst.result.contexts = [
            {
                "name": "c1",
                "context_def_name": "ctx",
                "context_vars": {"a": "10", "b": "z"},
                "foms": [{"name": "F", "value": 1, "origin_type": "app"}],
            },
            {
                "name": "c2",
                "context_def_name": "ctx",
                "context_vars": {"a": "2", "b": "a"},
                "foms": [{"name": "F", "value": 2, "origin_type": "app"}],
            },
            {
                "name": "c3",
                "context_def_name": "ctx",
                "context_vars": {"a": "10", "b": "m"},
                "foms": [{"name": "F", "value": 3, "origin_type": "app"}],
            },
            {
                "name": "c4",
                "context_def_name": "ctx",
                "context_vars": {"a": "not-a-number", "b": "x"},
                "foms": [{"name": "F", "value": 4, "origin_type": "app"}],
            },
        ]

        table.extract_row(app_inst)

        col_names = list(table._data.keys())
        # Expected order:
        # a=2, b=a (numeric 2)
        # a=10, b=m (numeric 10)
        # a=10, b=z (numeric 10)
        # a=not-a-number, b=x (string)
        expected_order = ["2-a", "10-m", "10-z", "not-a-number-x"]
        self.assertEqual(col_names, expected_order)

    def test_autocolumn_regex_groups(self):
        conf_dict = {
            "name": "table",
            "autocolumns": [
                {
                    "name": "{fom_name} ({size})",
                    "context_name": "ctx-(?P<size>.*)",
                    "figure_of_merit": "(?P<fom_name>.*)",
                }
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True

        def side_effect(var, extra_vars=None):
            if extra_vars:
                res = var
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
                return res
            return var

        app_inst.expander.expand_var.side_effect = side_effect

        app_inst.result.contexts = [
            {
                "name": "ctx-small",
                "context_def_name": "ctx-64",
                "context_vars": {},
                "foms": [{"name": "BW", "value": 100, "origin_type": "app"}],
            }
        ]

        table.extract_row(app_inst)

        self.assertIn("BW (64)", table._data)
        self.assertEqual(table._data["BW (64)"], [100])

    def test_autocolumn_null_context(self):
        conf_dict = {
            "name": "table",
            "autocolumns": [{"name": "{fom_name}", "figure_of_merit": "*"}],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True
        app_inst.expander.expand_var.side_effect = lambda x, extra_vars=None: (
            extra_vars["fom_name"] if extra_vars and "fom_name" in extra_vars else x
        )

        app_inst.result.contexts = [
            {
                "name": "null",
                "context_def_name": None,
                "context_vars": {},
                "foms": [{"name": "GlobalFOM", "value": 500, "origin_type": "app"}],
            }
        ]

        table.extract_row(app_inst)

        self.assertIn("GlobalFOM", table._data)
        self.assertEqual(table._data["GlobalFOM"], [500])

    def test_autocolumn_origin_filter(self):
        conf_dict = {
            "name": "table",
            "autocolumns": [
                {
                    "name": "{fom_name}",
                    "context_name": "ctx",
                    "figure_of_merit": "*",
                    "figure_of_merit_origin_type": "application",
                }
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True
        app_inst.expander.expand_var.side_effect = lambda x, extra_vars=None: (
            extra_vars["fom_name"] if extra_vars and "fom_name" in extra_vars else x
        )

        app_inst.result.contexts = [
            {
                "name": "ctx",
                "context_def_name": "ctx",
                "context_vars": {},
                "foms": [
                    {"name": "AppFOM", "value": 1, "origin_type": "application"},
                    {"name": "SysFOM", "value": 2, "origin_type": "system"},
                ],
            }
        ]

        table.extract_row(app_inst)

        self.assertIn("AppFOM", table._data)
        self.assertNotIn("SysFOM", table._data)

    def test_autocolumn_context_name_variable(self):
        conf_dict = {
            "name": "table",
            "autocolumns": [
                {
                    "name": "{context_name} - {fom_name}",
                    "context_name": "ctx*",
                    "figure_of_merit": "*",
                }
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True

        def side_effect(var, extra_vars=None):
            if extra_vars:
                res = var
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
                return res
            return var

        app_inst.expander.expand_var.side_effect = side_effect

        app_inst.result.contexts = [
            {
                "name": "ctx-A",
                "context_def_name": "ctx1",
                "context_vars": {},
                "foms": [{"name": "F1", "value": 1, "origin_type": "app"}],
            },
            {
                "name": "ctx-B",
                "context_def_name": "ctx2",
                "context_vars": {},
                "foms": [{"name": "F2", "value": 2, "origin_type": "app"}],
            },
        ]

        table.extract_row(app_inst)

        self.assertIn("ctx-A - F1", table._data)
        self.assertIn("ctx-B - F2", table._data)
        self.assertEqual(table._data["ctx-A - F1"], [1])
        self.assertEqual(table._data["ctx-B - F2"], [2])

    def test_autocolumn_match_instance_name_regex(self):
        conf_dict = {
            "name": "table",
            "autocolumns": [
                {
                    "name": "Step {num} FOM",
                    "context_name": "Step (?P<num>[0-9]+)",
                    "figure_of_merit": "F1",
                }
            ],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True

        def side_effect(var, extra_vars=None):
            if extra_vars:
                res = var
                for k, v in extra_vars.items():
                    res = res.replace(f"{{{k}}}", str(v))
                return res
            return var

        app_inst.expander.expand_var.side_effect = side_effect

        app_inst.result.contexts = [
            {
                "name": "Step 123",
                "context_def_name": "step_context",
                "context_vars": {},
                "foms": [{"name": "F1", "value": 99, "origin_type": "app"}],
            }
        ]

        table.extract_row(app_inst)

        self.assertIn("Step 123 FOM", table._data)
        self.assertEqual(table._data["Step 123 FOM"], [99])

    def test_table_transpose(self):
        conf_dict = {
            "name": "table",
            "transpose": True,
            "columns": [{"name": "Col1", "expression": "Val1"}],
        }
        table = ResultsTable(conf_dict)

        app_inst = MagicMock()
        app_inst.expander.evaluate_predicate.return_value = True
        app_inst.expander.expand_var.side_effect = lambda x, extra_vars=None: x

        table.extract_row(app_inst)

        # Mock pandas to verify transpose was called
        with patch("ramble.results_table.import_pandas") as mock_import:
            pd = MagicMock()
            mock_import.return_value = pd
            df = MagicMock()
            pd.DataFrame.return_value = df
            df.columns = ["Col1"]

            table._to_dataframe()

            df.transpose.assert_called_once()


if __name__ == "__main__":
    unittest.main()
