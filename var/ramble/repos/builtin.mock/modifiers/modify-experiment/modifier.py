# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class ModifyExperiment(BasicModifier):
    """Define a modifier which changes the experiment definition"""

    name = "modify-experiment"

    tags("test")

    mode("test1", description="This is a test mode")
    mode("test2", description="This is a test mode")
    mode("auto", description="This mode changes to an auto-detected mode")
    default_mode("auto")

    def modify_experiment(self, app):
        if self._usage_mode == "auto":
            n_nodes = app.expander.expand_var_name("n_nodes", typed=True)
            if n_nodes > 1:
                self.set_usage_mode("test2")
            else:
                self.set_usage_mode("test1")

        if self._usage_mode == "test1":
            app.define_variable("n_ranks", 5)
        elif self._usage_mode == "test2":
            app.define_variable("n_ranks", 10)
        else:
            logger.die(
                f"Usage mode for {self.name} is {self._usage_mode} which is invalid."
            )
