# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import glob
import inspect

from spack.directives import extends
from spack.package import PackageBase, run_after


class RubyPackage(PackageBase):
    """Specialized class for building Ruby gems.

    This class provides two phases that can be overridden if required:

    #. :py:meth:`~.RubyPackage.build`
    #. :py:meth:`~.RubyPackage.install`
    """

    maintainers = ['Kerilk']

    #: Phases of a Ruby package
    phases = ['build', 'install']

    #: This attribute is used in UI queries that need to know the build
    #: system base class
    build_system_class = 'RubyPackage'

    extends('ruby')

    def build(self, spec, prefix):
        """Build a Ruby gem."""

        # ruby-rake provides both rake.gemspec and Rakefile, but only
        # rake.gemspec can be built without an existing rake installation
        gemspecs = glob.glob('*.gemspec')
        rakefiles = glob.glob('Rakefile')
        if gemspecs:
            inspect.getmodule(self).gem('build', '--norc', gemspecs[0])
        elif rakefiles:
            jobs = inspect.getmodule(self).make_jobs
            inspect.getmodule(self).rake('package', '-j{0}'.format(jobs))
        else:
            # Some Ruby packages only ship `*.gem` files, so nothing to build
            pass

    def install(self, spec, prefix):
        """Install a Ruby gem.

        The ruby package sets ``GEM_HOME`` to tell gem where to install to."""

        gems = glob.glob('*.gem')
        if gems:
            # if --install-dir is not used, GEM_PATH is deleted from the
            # environement, and Gems required to build native extensions will
            # not be found. Those extensions are built during `gem install`.
            inspect.getmodule(self).gem(
                'install', '--norc', '--ignore-dependencies',
                '--install-dir', prefix, gems[0])

    # Check that self.prefix is there after installation
    run_after('install')(PackageBase.sanity_check_prefix)
