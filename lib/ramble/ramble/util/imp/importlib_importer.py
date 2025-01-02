# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Implementation of Ramble imports that uses importlib underneath.

``importlib`` is only fully implemented in Python 3.
"""
from importlib.machinery import SourceFileLoader  # novm
import types


class PrependFileLoader(SourceFileLoader):
    def __init__(self, full_name, path, prepend=None):
        super().__init__(full_name, path)
        self.prepend = prepend

    def path_stats(self, path):
        stats = super().path_stats(path)
        if self.prepend:
            stats["size"] += len(self.prepend) + 1
        return stats

    def get_data(self, path):
        data = super().get_data(path)
        if path != self.path or self.prepend is None:
            return data
        else:
            return self.prepend.encode() + b"\n" + data


def load_source(full_name, path, prepend=None):
    """Import a Python module from source.

    Load the source file and add it to ``sys.modules``.

    Args:
        full_name (str): full name of the module to be loaded
        path (str): path to the file that should be loaded
        prepend (str, optional): some optional code to prepend to the
            loaded module; e.g., can be used to inject import statements

    Returns:
        (ModuleType): the loaded module
    """
    # use our custom loader
    loader = PrependFileLoader(full_name, path, prepend)
    mod = types.ModuleType(loader.name)
    loader.exec_module(mod)
    return mod
