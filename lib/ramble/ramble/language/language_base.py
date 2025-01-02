# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""This package contains the underlying implementation for the language
directives, which are to allow functions to be invoked at class level
"""

import functools

import llnl.util.lang
import llnl.util.tty.color

import ramble.error

from collections.abc import Sequence  # novm


__all__ = ["DirectiveMeta", "DirectiveError"]


#: These are variant names used by ramble internally; applications can't use
#: them
reserved_names = []

namespaces = ["ramble.app", "ramble.mod", "ramble.pkg_man", "ramble.package_manager"]


class DirectiveMeta(type):
    """Flushes the directives that were temporarily stored in the staging
    area into the package.
    """

    # Set of all known directives
    _directive_names = set()
    _directives_to_be_executed = []
    _directive_functions = {}
    _directive_classes = {}

    def __new__(cls, name, bases, attr_dict):
        # Initialize the attribute containing the list of directives
        # to be executed. Here we go reversed because we want to execute
        # commands:
        # 1. in the order they were defined
        # 2. following the MRO
        attr_dict["_directives_to_be_executed"] = []
        for base in reversed(bases):
            try:
                directive_from_base = base._directives_to_be_executed
                attr_dict["_directives_to_be_executed"].extend(directive_from_base)
            except AttributeError:
                # The base class didn't have the required attribute.
                # Continue searching
                pass

        # De-duplicates directives from base classes
        attr_dict["_directives_to_be_executed"] = [
            x for x in llnl.util.lang.dedupe(attr_dict["_directives_to_be_executed"])
        ]

        # Move things to be executed from module scope (where they
        # are collected first) to class scope
        if DirectiveMeta._directives_to_be_executed:
            attr_dict["_directives_to_be_executed"].extend(
                DirectiveMeta._directives_to_be_executed
            )
            DirectiveMeta._directives_to_be_executed = []

        return super().__new__(cls, name, bases, attr_dict)

    def __init__(cls, name, bases, attr_dict):
        # The instance is being initialized: if it is a package we must ensure
        # that the directives are called to set it up.

        valid_module = False
        for namespace in namespaces:
            if namespace in cls.__module__:
                valid_module = True

        if valid_module:
            # Ensure the presence of the dictionaries associated
            # with the directives
            for d in DirectiveMeta._directive_names:
                setattr(cls, d, {})

            directive_attrs = {
                "_directive_functions": {},
                "_directive_classes": {},
                "_directive_names": DirectiveMeta._directive_names.copy(),
            }

            for attr in directive_attrs.keys():
                if hasattr(DirectiveMeta, attr):
                    directive_attrs[attr].update(getattr(DirectiveMeta, attr))

            for attr in directive_attrs.keys():
                setattr(cls, attr, directive_attrs[attr])

            # Lazily execute directives
            for directive in cls._directives_to_be_executed:
                directive(cls)

            # Ignore any directives executed *within* top-level
            # directives by clearing out the queue they're appended to
            DirectiveMeta._directives_to_be_executed = []

        super().__init__(name, bases, attr_dict)

    @classmethod
    def directive(cls, dicts=None):
        """Decorator for Ramble directives.

        Ramble directives allow you to modify an object while it is being
        defined, e.g. to add version or dependency information.  Directives are
        one of the key pieces of Ramble's object "language", which is
        embedded in python.

        Here's an example directive:

        .. code-block:: python

            @directive(dicts='workloads')
            workload('workload_name', ...):
                ...

        This directive allows you write:

        .. code-block:: python

            class Foo(ApplicationBase):
                workload(...)

        The ``@directive`` decorator handles a couple things for you:

          1. Adds the class scope (app) as an initial parameter when
             called, like a class method would.  This allows you to modify
             a package from within a directive, while the package is still
             being defined.

          2. It automatically adds a dictionary called "workloads" to the
             package so that you can refer to app.workloads.

        The ``(dicts='workloads')`` part ensures that ALL applications in
        Ramble will have a ``workloads`` attribute after they're constructed,
        and that if no directive actually modified it, it will just be an empty
        dict.

        This is just a modular way to add storage attributes to the Application
        class, and it's how Ramble gets information from the applications to
        the core.

        """
        if isinstance(dicts, str):
            dicts = (dicts,)

        if not isinstance(dicts, Sequence):
            message = "dicts arg must be list, tuple, or string. Found {0}"
            raise TypeError(message.format(type(dicts)))

        # Add the dictionary names if not already there
        DirectiveMeta._directive_names |= set(dicts)

        # This decorator just returns the directive functions
        def _decorator(decorated_function):
            @functools.wraps(decorated_function)
            def _wrapper(*args, **kwargs):
                # If any of the arguments are executors returned by a
                # directive passed as an argument, don't execute them
                # lazily. Instead, let the called directive handle them.
                # This allows nested directive calls in applications.  The
                # caller can return the directive if it should be queued.
                def remove_directives(arg):
                    directives = DirectiveMeta._directives_to_be_executed
                    if isinstance(arg, (list, tuple)):
                        # Descend into args that are lists or tuples
                        for a in arg:
                            remove_directives(a)
                    else:
                        # Remove directives args from the exec queue
                        remove = next((d for d in directives if d is arg), None)
                        if remove is not None:
                            directives.remove(remove)

                # Nasty, but it's the best way I can think of to avoid
                # side effects if directive results are passed as args
                remove_directives(args)
                remove_directives(list(kwargs.values()))

                # A directive returns either something that is callable on a
                # package or a sequence of them
                result = decorated_function(*args, **kwargs)

                # ...so if it is not a sequence make it so
                values = result
                if not isinstance(values, Sequence):
                    values = (values,)

                DirectiveMeta._directives_to_be_executed.extend(values)

                # wrapped function returns same result as original so
                # that we can nest directives
                return result

            DirectiveMeta._directive_classes[decorated_function.__name__] = cls
            DirectiveMeta._directive_functions[decorated_function.__name__] = decorated_function

            return _wrapper

        return _decorator


class DirectiveError(ramble.error.RambleError):
    """This is raised when something is wrong with a language directive."""
