# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
import os

from ramble.util.file_util import create_symlink
from ramble.util.logger import logger
from ramble.util.module_utils import import_pandas


class ResultsColumn:
    """Class representing a single column in a results table"""

    _where_name = "where"
    _column_attrs = [
        "name",
        "expression",
        "figure_of_merit",
        "figure_of_merit_context",
        "figure_of_merit_origin_type",
    ]

    def __init__(self, conf_dict):
        """Construct a column from a configuration dict, assuming the structure matches the
        column schema in lib/ramble/ramble/schema/tables.py

        Args:
            conf_dict (dict): dictionary structured like the column schema in tables.py

        """
        # Extract column attributes
        for attr in self._column_attrs:
            setattr(self, attr, str(conf_dict[attr]) if attr in conf_dict else None)

        if self.expression and self.figure_of_merit:
            logger.die(
                "Results columns cannot have both 'expression' and 'figure_of_merit' attributes"
            )

        if not self.expression and not self.figure_of_merit:
            logger.die(
                "One of either 'expression' or 'figure_of_merit' are required for each "
                "column definition"
            )

        self.where = []
        if self._where_name in conf_dict:
            self.where.extend(conf_dict[self._where_name])

    def col_name(self, app_inst):
        """Expand this columns name based on the current experiment

        Args:
            app_inst: Instance of an application class to expand name with

        Returns:
            (str): Expanded column name
        """
        return app_inst.expander.expand_var(self.name)

    def extract_value(self, app_inst, extra_vars=None):
        """Extract this column's value based on an application instance and other column values

        Args:
            app_inst: Instance of an application class
            extra_vars: Dictionary containing additional variables to expand with

            iteration (Union[None, str]): The iteration to search for.
            instance (Union[None, str]): The instance to search for.
        """
        if extra_vars is None:
            extra_vars = {}

        value = None

        action_experiment = True
        for expression in self.where:
            if not app_inst.expander.evaluate_predicate(expression):
                action_experiment = False

        if not action_experiment:
            return value

        if self.expression:
            value = app_inst.expander.expand_var(self.expression, extra_vars=extra_vars)
        elif self.figure_of_merit:
            fom_name = self.figure_of_merit
            context_name = None
            if self.figure_of_merit_context:
                context_name = app_inst.expander.expand_var(self.figure_of_merit_context)

            origin_type = None
            if self.figure_of_merit_origin_type:
                origin_type = app_inst.expander.expand_var(self.figure_of_merit_origin_type)

            results = app_inst.result
            for context in results.contexts:
                if context_name is None or context_name == context["name"]:
                    for fom in context["foms"]:
                        if fom["name"] == fom_name:
                            keep = True
                            if origin_type and origin_type != fom["origin_type"]:
                                keep = False

                            if keep:
                                if value is not None:
                                    logger.warn(
                                        "Non-unique values found " f"for column {self.name}"
                                    )
                                value = fom["value"]
        return value


class ResultsTable:
    """A single results table based on the tables.py schema"""

    _default_group_method = "max"
    _group_method_name = "group_method"
    _group_by_name = "group_by"
    _sort_by_name = "sort_by"
    _columns_name = "columns"
    _where_name = "where"

    def __init__(self, conf_dict):
        """Constructor for a single table

        Args:
            conf_dict (dict): Configuration dictionary based on the table schema in tables.py
        """
        self._num_rows = 0
        self._data = {}

        self.name = conf_dict["name"]

        self.group_method = self._default_group_method
        if self._group_method_name in conf_dict:
            self.group_method = conf_dict[self._group_method_name]

        # Build group_by and sort_by attrs
        for set_name in ["group", "sort"]:
            temp_list = []
            set_name_attr = getattr(self, f"_{set_name}_by_name")
            if set_name_attr in conf_dict:
                if isinstance(conf_dict[set_name_attr], list):
                    temp_list.extend(conf_dict[set_name_attr])
                else:
                    temp_list.append(conf_dict[set_name_attr])
            setattr(self, f"{set_name}_by", temp_list)

        # Build table where statements
        self.where = []
        if self._where_name in conf_dict:
            self.where.extend(conf_dict[self._where_name])

        # Build table columns
        self.columns = []
        if self._columns_name in conf_dict:
            for column_config in conf_dict[self._columns_name]:
                self.columns.append(ResultsColumn(column_config))

    def render(self, app_inst):
        new_table = copy.deepcopy(self)
        new_table.name = app_inst.expander.expand_var(self.name)
        return new_table

    def table_name(self, app_inst):
        """Determine the name for this table, based on a given experiment

        Args:
            app_inst: Instance of an application class

        Returns:
            (str): Name of table
        """

        return app_inst.expander.expand_var(self.name)

    def add_where(self, expressions):
        """Add a where expression to this table

        Args:
            expression (Union[List[str], str]): The regular expression to search for.
        """

        if not expressions:
            return

        if isinstance(expressions, list):
            self.where.extend(expressions)
        else:
            self.where.append(expressions)

    def includes_experiment(self, app_inst):
        """Determine if an experiment is included in this table.

        Args:
            app_inst: Instance of an application class

        Returns:
            (bool): True if the app_inst is included in table, False otherwise
        """

        include_experiment = True

        for expression in self.where:
            if not app_inst.expander.evaluate_predicate(expression):
                include_experiment = False

        return include_experiment

    def extract_row(self, app_inst):
        """Extract a row of data from an experiment

        Args:
            app_inst: Instance of an application class to extract data from
        """
        column_values = {}
        remaining_columns = set(self._data.keys())

        for column in self.columns:
            col_value = column.extract_value(app_inst, extra_vars=column_values)

            if col_value is None:
                continue

            col_name = column.col_name(app_inst)

            if col_name in remaining_columns:
                remaining_columns.remove(col_name)
                self._data[col_name].append(col_value)

            elif col_name not in self._data.keys():
                self._data[col_name] = [None] * self._num_rows + [col_value]

            column_values[col_name] = col_value

        for col_name in remaining_columns:
            self._data[col_name].append(None)

        self._num_rows += 1

    def _to_dataframe(self):
        """Construct a pandasdata frame from this table's data"""
        pd = import_pandas()
        self._df = pd.DataFrame(self._data)

        for column in self._df.columns:
            try:
                self._df[column] = pd.to_numeric(self._df[column])
            except ValueError:
                pass

    def _group_dataframe(self):
        """Apply any grouping to this pandas dataframe"""
        if self.group_by:
            try:
                grouped_df = self._df.groupby(*self.group_by, as_index=False)

                group_func = getattr(grouped_df, self.group_method, grouped_df.max)
                self._df = group_func()
            except KeyError:
                pass

    def _sort_dataframe(self):
        """Apply any sorting to this pandas dataframe"""
        if self.sort_by:
            try:
                self._df = self._df.sort_values(by=self.sort_by)
            except KeyError:
                pass

    def to_csv(self, directory, timestamp):
        """CSV converter for results table

        Args:
            directory (str): Directory to write tabular data into
            timestamp (str): Timestamp to apply to table output files
        """
        self._to_dataframe()
        self._group_dataframe()
        self._sort_dataframe()

        extension = "csv"
        inner_delim = "."
        filename = self.name + inner_delim + timestamp + inner_delim + extension
        latestname = self.name + inner_delim + "latest" + inner_delim + extension
        file_path = os.path.join(directory, filename)
        latest_path = os.path.join(directory, latestname)
        self._df.to_csv(file_path, index=False)

        create_symlink(file_path, latest_path)
        return file_path, latest_path


class ResultsTables:
    """Class representing a set of results tables"""

    def __init__(self):
        self.table_templates = []
        self.tables = {}

    @property
    def num_tables(self):
        return len(self.table_templates)

    def add_table_template(self, table_conf):
        """Construct a new results table, and add to this set of tables

        Args:
            table_conf (dict): Dictionary configuration of table,
                               assuming table schema from tables.py

        Returns:
            (ResultsTable): New table instance
        """
        new_table = ResultsTable(table_conf)
        self.table_templates.append(new_table)
        return new_table

    def all_table_templates(self):
        """Yield all table templates

        Yields:
            (ResultsTable): All of the results table templates
        """

        yield from self.table_templates

    def build_tables(self, experiment_set, filters):
        """Extract data for each table in this set

        Args:
            experiment_set: Set of experiments to extract data from
            filters: Filter object to downselect experiments
        """
        for _, app_inst, _ in experiment_set.filtered_experiments(filters):
            for table_template in self.table_templates:
                if table_template.includes_experiment(app_inst):
                    table_name = table_template.table_name(app_inst)

                    if table_name not in self.tables:
                        self.tables[table_name] = table_template.render(app_inst)

                    self.tables[table_name].extract_row(app_inst)

    def output_tables(self, directory, timestamp):
        """Output tabular data for each of the tables in this set

        Args:
            directory (str): Directory to write tables into
            timestamp (str): Timestamp to apply to table output files
        """
        table_files = []
        table_symlinks = []
        for table in self.tables.values():
            table_file, table_symlink = table.to_csv(directory, timestamp)
            table_files.append(table_file)
            table_symlinks.append(table_symlink)

        if table_files:
            logger.all_msg("Tables written:")
            for file in table_files:
                logger.all_msg(f"  {file}")

            logger.all_msg("Table symlinks updated:")
            for symlink in table_symlinks:
                logger.all_msg(f"  {symlink}")
