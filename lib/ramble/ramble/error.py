# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
from __future__ import print_function

import sys
import inspect

import llnl.util.tty as tty


#: whether we should write stack traces or short error messages
#: this is module-scoped because it needs to be set very early
debug = False


class RambleError(Exception):
    """This is the superclass for all Ramble errors.
       Subclasses can be found in the modules they have to do with.
    """

    def __init__(self, message, long_message=None):
        super(RambleError, self).__init__()
        self.message = message
        self._long_message = long_message

        # for exceptions raised from child build processes, we save the
        # traceback as a string and print it in the parent.
        self.traceback = None

        # we allow exceptions to print debug info via print_context()
        # before they are caught at the top level. If they *haven't*
        # printed context early, we do it by default when die() is
        # called, so we need to remember whether it's been called.
        self.printed = False

    @property
    def long_message(self):
        return self._long_message

    def print_context(self):
        """Print extended debug information about this exception.

        This is usually printed when the top-level Ramble error handler
        calls ``die()``, but it can be called separately beforehand if a
        lower-level error handler needs to print error context and
        continue without raising the exception to the top level.
        """
        if self.printed:
            return

        # basic debug message
        tty.error(self.message)
        if self.long_message:
            sys.stderr.write(self.long_message)
            sys.stderr.write('\n')

        # stack trace, etc. in debug mode.
        if debug:
            if self.traceback:
                # exception came from a build child, already got
                # traceback in child, so print it.
                sys.stderr.write(self.traceback)
            else:
                # run parent exception hook.
                sys.excepthook(*sys.exc_info())

        sys.stderr.flush()
        self.printed = True

    def die(self):
        self.print_context()
        sys.exit(1)

    def __str__(self):
        msg = self.message
        if self._long_message:
            msg += "\n    %s" % self._long_message
        return msg

    def __repr__(self):
        args = [repr(self.message), repr(self.long_message)]
        args = ','.join(args)
        qualified_name = inspect.getmodule(
            self).__name__ + '.' + type(self).__name__
        return qualified_name + '(' + args + ')'

    def __reduce__(self):
        return type(self), (self.message, self.long_message)


class SpecError(RambleError):
    """Superclass for all errors that occur while constructing specs."""
