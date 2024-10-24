# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.modifier import ModifierBase


class DisabledModifier(ModifierBase):
    """Specialized class for disabled modifiers.

    This class can be used to create a disabled modifier from an active
    modifier instance.
    """

    modifier_class = "DisabledModifier"

    disabled = True

    name = "disabled"

    def __init__(self, instance_to_disable):
        super().__init__(instance_to_disable._file_path)

        self.name = instance_to_disable.name
        self.maintainers = instance_to_disable.maintainers.copy()
        self.tags = instance_to_disable.tags.copy()

    def define_variable(self, var_name, var_value):
        """Given this modifier is disabled, never define variables in it"""
        pass
