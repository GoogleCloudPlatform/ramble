# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import sys


def this_is_a_function():
    """This is a docstring."""

    def this_should_be_offset():
        sys.stdout.write(os.name)
