# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# TODO Define language features
"""This package contains directives that can be used within a package.

Directives are functions that can be called inside a package
definition to modify the package, for example:

    class Gromacs(MpiRunApplication):
        workload('water_bare_hbonds_1536')
        ...

    'workload' is a ramble directive

The available directives are:

    <TO BE IMPLEMENTED>

"""

import functools
import sys

from six import string_types

import llnl.util.lang
import llnl.util.tty.color

import ramble.error

if sys.version_info >= (3, 3):
    from collections.abc import Sequence  # novm
else:
    from collections import Sequence


__all__ = ['DirectiveMeta', 'DirectiveError']


#: These are variant names used by ramble internally; applications can't use
#: them
reserved_names = []


class DirectiveMeta(type):
    """Flushes the directives that were temporarily stored in the staging
    area into the package.
    """

    # Set of all known directives
    _directive_names = set()
    _directives_to_be_executed = []

    def __new__(cls, name, bases, attr_dict):
        # Initialize the attribute containing the list of directives
        # to be executed. Here we go reversed because we want to execute
        # commands:
        # 1. in the order they were defined
        # 2. following the MRO

        attr_dict['_directives_to_be_executed'] = []

        meta_stack = []
        meta_stack.extend(cls.__bases__)
        meta_list = []
        while meta_stack:
            cur_meta = meta_stack.pop(0)

            meta_stack.extend(cur_meta.__bases__)

            if hasattr(cur_meta, '_directives_to_be_executed'):
                meta_list.append(cur_meta)

        for meta in meta_list:
            try:
                directives = meta._directives_to_be_executed
                attr_dict['_directives_to_be_executed'].extend(directives)
                meta._directives_to_be_executed = []
            except AttributeError:
                pass

            for directive in meta._directive_names:
                if directive not in cls._directive_names:
                    cls._directive_names |= set((directive,))

        for base in reversed(bases):
            try:
                directive_from_base = base._directives_to_be_executed
                attr_dict['_directives_to_be_executed'].extend(
                    directive_from_base)
            except AttributeError:
                # The base class didn't have the required attribute.
                # Continue searching
                pass

        # De-duplicates directives from base classes
        attr_dict['_directives_to_be_executed'] = [
            x for x in llnl.util.lang.dedupe(
                attr_dict['_directives_to_be_executed'])]

        # Move things to be executed from module scope (where they
        # are collected first) to class scope
        if cls._directives_to_be_executed:
            attr_dict['_directives_to_be_executed'].extend(
                cls._directives_to_be_executed)
            cls._directives_to_be_executed = []

        return super(DirectiveMeta, cls).__new__(
            cls, name, bases, attr_dict)

    def __init__(cls, name, bases, attr_dict):
        # The instance is being initialized: if it is a package we must ensure
        # that the directives are called to set it up.

        if 'ramble.app' in cls.__module__:
            # Ensure the presence of the dictionaries associated
            # with the directives
            for d in cls._directive_names:
                setattr(cls, d, {})

            # Lazily execute directives
            for directive in cls._directives_to_be_executed:
                directive(cls)

            # Ignore any directives executed *within* top-level
            # directives by clearing out the queue they're appended to
            cls._directives_to_be_executed = []

        super().__init__(name, bases, attr_dict)

    @classmethod
    def directive(cls, dicts=None):
        """Decorator for Ramble directives.

        Ramble directives allow you to modify a package while it is being
        defined, e.g. to add version or dependency information.  Directives are
        one of the key pieces of Ramble's appliaction "language", which is
        embedded in python.

        Here's an example directive:

            @directive(dicts='workloads')
            workload('workload_name', ...):
                ...

        This directive allows you write:

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

        This is just a modular way to add storage attributes to the Appliaction
        class, and it's how Ramble gets information from the applications to
        the core.

        """
        if isinstance(dicts, string_types):
            dicts = (dicts, )
        if not isinstance(dicts, Sequence):
            message = "dicts arg must be list, tuple, or string. Found {0}"
            raise TypeError(message.format(type(dicts)))
        # Add the dictionary names if not already there
        cls._directive_names |= set(dicts)

        # This decorator just returns the directive functions
        def _decorator(decorated_function):
            mod = sys.modules[decorated_function.__module__]

            if hasattr(mod, '__all__'):
                mod.__all__.append(decorated_function.__name__)
            else:
                mod.__all__ = [decorated_function.__name__]
            # __all__.append(decorated_function.__name__)

            @functools.wraps(decorated_function)
            def _wrapper(*args, **kwargs):
                # If any of the arguments are executors returned by a
                # directive passed as an argument, don't execute them
                # lazily. Instead, let the called directive handle them.
                # This allows nested directive calls in applications.  The
                # caller can return the directive if it should be queued.
                def remove_directives(arg):
                    directives = cls._directives_to_be_executed
                    if isinstance(arg, (list, tuple)):
                        # Descend into args that are lists or tuples
                        for a in arg:
                            remove_directives(a)
                    else:
                        # Remove directives args from the exec queue
                        remove = next(
                            (d for d in directives if d is arg), None)
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
                    values = (values, )

                cls._directives_to_be_executed.extend(values)

                # wrapped function returns same result as original so
                # that we can nest directives
                return result
            return _wrapper

        return _decorator


class DirectiveError(ramble.error.RambleError):
    """This is raised when something is wrong with a language directive."""
