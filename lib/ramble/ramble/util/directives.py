# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def define_directive_methods_on_class(cls):
    """Create class methods that execute directives on the class.

    Wrap each directive, and inject it into this class as a method.
    """
    if not hasattr(cls, "_directive_classes") or not hasattr(cls, "_directive_functions"):
        return

    for directive, directive_class in cls._directive_classes.items():
        is_valid_lang = False
        if hasattr(cls, "_language_classes"):
            for lang_class in cls._language_classes:
                if directive_class is lang_class:
                    is_valid_lang = True

        if not hasattr(cls, directive) and is_valid_lang:
            setattr(cls, directive, wrap_named_directive_class_level(directive))


def wrap_named_directive_class_level(name):
    """Wrap a directive to simplify execution at the class level

    Create a bound-like method that executes a directive on the instance
    """

    def _execute_directive(self, *args, directive_name=name, **kwargs):
        self._directive_functions[directive_name](*args, **kwargs)(self)

    return _execute_directive
