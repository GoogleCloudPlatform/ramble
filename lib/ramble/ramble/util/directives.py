# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def define_directive_methods(obj_inst):
    """Create class methods that execute directives

    Wrap each directive, and inject it into this class instance as a class
    method.

    This allows:

    self.<directive_name>(<directive_args>) to be called. As in:

    self.archive_pattern('*.log')

    Which can be called within `def __init__(self, file_path)` instead of
    having to call `archive_pattern('*.log')` at the class definition level.

    This function requires the object instance to have internal attributes:
    - '_directive_classes' - Dictionary mapping a directive to the class the
      directive is defined for
    - '_directive_functions' - Dictionary mapping a directive to the decorated function
      that defines the directive
    - '_language_classes' - A list of classes that language features should be "imported" from

    Both '_directive_classes' and '_directive_functions' are defined for all
    classes that use the DirectiveMeta meta-class.

    The '_language_classes' attribute is defined in ApplicationBase and ModifierBase.
    """
    if not hasattr(obj_inst, "_directive_classes") or not hasattr(
        obj_inst, "_directive_functions"
    ):
        return

    for directive, directive_class in obj_inst._directive_classes.items():
        is_valid_lang = False
        if hasattr(obj_inst, "_language_classes"):
            for lang_class in obj_inst._language_classes:
                if directive_class is lang_class:
                    is_valid_lang = True

        if not hasattr(obj_inst, directive) and is_valid_lang:
            setattr(obj_inst, directive, wrap_named_directive(obj_inst, directive))


def wrap_named_directive(obj_inst, name):
    """Wrap a directive to simplify execution

    Create a wrapper method that executes a directive, to inject the
    `(self)` argument to simplify use of directives as class methods
    """

    def _execute_directive(*args, directive_name=name, **kwargs):
        obj_inst._directive_functions[directive_name](*args, **kwargs)(obj_inst)

    return _execute_directive
