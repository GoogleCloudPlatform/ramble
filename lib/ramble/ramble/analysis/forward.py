# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Define the forward-reading analysis strategy"""

import os
import string

import ramble.util.lock as lk
from ramble.analysis.base import AnalysisStrategyBase
from ramble.util.foms import NULL_CONTEXT as _NULL_CONTEXT
from ramble.util.logger import logger


class ForwardAnalysisStrategy(AnalysisStrategyBase):
    """Forward regex-based analysis/extraction strategy."""

    def __call__(self, workspace):
        app = self.app_inst

        prepared = self._prepare_analysis(workspace)
        if prepared is None:
            return
        criteria_list, files, f_defs, inmem_defs = prepared

        def format_context(context_match, context_format):
            context_val = {}
            if isinstance(context_format, str):
                for group in string.Formatter().parse(context_format):
                    if group[1]:
                        context_val[group[1]] = context_match[group[1]]

            context_string = context_format.format(**context_val)
            return context_string

        exp_lock = app.experiment_lock
        fom_values, context_metadata, null_key = self._init_fom_containers()

        # Iterate over files. We already know they exist
        with lk.ReadTransaction(exp_lock):
            for file, file_conf in files.items():

                # Start with no active contexts in a file.
                active_contexts = {}
                logger.debug(f"Reading log file: {file}")

                if not os.path.exists(file):
                    logger.debug(f"Skipping analysis of non-existent file: {file}")
                    continue

                per_file_crit_objs = [
                    criteria_list.find_criteria(c) for c in file_conf["success_criteria"]
                ]

                with open(file, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        per_file_crit_objs = self._update_per_file_criteria(
                            line, per_file_crit_objs
                        )

                        # Iterate over contexts and add matched contexts to active_contexts
                        for context, foms in file_conf["contexts"].items():
                            if context != _NULL_CONTEXT:
                                context_conf = f_defs[context]["definition"]
                                if context_conf.get("pre_filter", "") not in line:
                                    context_match = None
                                else:
                                    context_match = context_conf["regex"].match(line)

                                if context_match:
                                    context_name = format_context(
                                        context_match,
                                        context_conf["format"],
                                    )
                                    logger.debug(f"Line was: {line}")
                                    logger.debug(f" Context match {context} -- {context_name}")

                                    context_vars = context_match.groupdict()
                                    context_key = (
                                        context_name,
                                        context,
                                        frozenset(context_vars.items()),
                                    )

                                    active_contexts[context] = context_key

                                    if context_key not in fom_values:
                                        fom_values[context_key] = {}
                                        context_metadata[context_key] = {
                                            "name": context_name,
                                            "def_name": context,
                                            "vars": context_vars,
                                        }

                            for fom in foms:
                                fom_conf = f_defs[context]["foms"][fom]
                                fom_context = (
                                    active_contexts.get(context, null_key)
                                    if fom_conf["contexts"]
                                    else null_key
                                )
                                self._extract_fom_from_line(
                                    line, fom, fom_conf, fom_context, fom_values
                                )

        self._finalize_analysis(
            workspace, criteria_list, f_defs, inmem_defs, fom_values, context_metadata
        )
