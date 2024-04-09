# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403
from ramble.util.logger import logger


class ModPhase(BasicModifier):
    """Define a modifier that defines a new phase with register_phase"""
    name = "mod-phase"

    tags('test')

    mode('test', description='This is a test mode')

    register_phase('first_phase', pipeline='setup', run_before=['get_inputs'])

    def _first_phase(self, workspace, app_inst=None):
        logger.all_msg('Inside a phase: first_phase')

    register_phase('after_make_experiments', pipeline='setup', run_after=['make_experiments'])

    def _after_make_experiments(self, workspace, app_inst=None):
        logger.all_msg('Inside a phase: after_make_experiments')
