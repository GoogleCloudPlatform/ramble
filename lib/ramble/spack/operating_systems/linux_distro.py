# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
import platform as py_platform
import re

from spack.version import Version

from ._operating_system import OperatingSystem


def kernel_version():
    """Return the kernel version as a Version object.
       Note that the kernel version is distinct from OS and/or
       distribution versions. For instance:
       >>> external.distro.id()
       'centos'
       >>> external.distro.version()
       '7'
       >>> platform.release()
       '5.10.84+'
    """
    # Strip '+' characters just in case we're running a
    # version built from git/etc
    clean_version = re.sub(r'\+', r'', py_platform.release())
    return Version(clean_version)


class LinuxDistro(OperatingSystem):
    """ This class will represent the autodetected operating system
        for a Linux System. Since there are many different flavors of
        Linux, this class will attempt to encompass them all through
        autodetection using the python module platform and the method
        platform.dist()
    """

    def __init__(self):
        try:
            # This will throw an error if imported on a non-Linux platform.
            import external.distro
            distname, version = external.distro.id(), external.distro.version()
        except ImportError:
            distname, version = 'unknown', ''

        # Grabs major version from tuple on redhat; on other platforms
        # grab the first legal identifier in the version field.  On
        # debian you get things like 'wheezy/sid'; sid means unstable.
        # We just record 'wheezy' and don't get quite so detailed.
        version = re.split(r'[^\w-]', version)

        if 'ubuntu' in distname:
            version = '.'.join(version[0:2])
        else:
            version = version[0]

        super(LinuxDistro, self).__init__(distname, version)
