# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import six

import llnl.util.tty as tty  # noqa: F401

import ramble.error

from ramble.schema.types import OUTPUT_CAPTURE


class CommandExecutable(object):
    """CommandExecutable class
    This class is used to represent internal executables in Ramble.

    These executables are portions of an experiment definition. They are
    generally used to group one or more commands together into an executable
    name.
    """
    def __init__(self, name, template, use_mpi=False, mpi=False, redirect='{log_file}',
                 output_capture=OUTPUT_CAPTURE.DEFAULT, **kwargs):
        """Create a CommandExecutable instance

        Args:
        - template: Either a string, or a list of strings representing
                    independent commands within this executable
        - use_mpi: Boolean value for if MPI should be applied to each
                   portion of this executable's template
        - mpi: Same as use_mpi
        - redirect: File to redirect output of template into
        - output_capture: Operator to use when capturing output
        """

        if isinstance(template, six.string_types):
            self.template = [template]
        elif isinstance(template, list):
            self.template = template.copy()
        else:
            raise CommandExecutableError('Command executable is given an '
                                         f'invalid template type of {type(template)}')

        self.name = name
        self.mpi = use_mpi or mpi
        self.redirect = redirect
        self.output_capture = output_capture

    def copy(self):
        """Replicate a CommandExecutable instance"""
        new_inst = type(self)(self.name, self.template, mpi=self.mpi,
                              redirect=self.redirect,
                              output_capture=self.output_capture)
        return new_inst

    def __str__(self):
        """String representation of CommandExecutable instance"""
        self_str = f'exec: {self.name}:\n' + \
                   f'    template: {str(self.template)}\n' + \
                   f'    mpi: {self.mpi}\n' +\
                   f'    redirect: {self.redirect}\n' +\
                   f'    output_capture: {self.output_capture}\n'

        return self_str


class CommandExecutableError(ramble.error.RambleError):
    """Class for errors when using command executable classes"""
