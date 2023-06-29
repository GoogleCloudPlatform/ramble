# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

from ramble.app.builtin.hpl import Hpl as HplApplication


class IntelHpl(HplApplication):
    '''Define HPL application using Intel MKL optimized binary from intel-oneapi-mpi package'''
    name = 'intel-hpl'

    maintainers('dodecatheon')

    tags('optimized', 'intel', 'mkl')

    default_compiler('gcc9', spack_spec='gcc@9.5.0')
    software_spec('imkl_2023p1', spack_spec='intel-oneapi-mkl@2023.1.0 threads=openmp')
    software_spec('impi_2018', spack_spec='intel-mpi@2018.4.274')

    # Note that 'hpl' is required by the Hpl class
    required_package('intel-oneapi-mkl')

    executable('execute',
               '{intel-oneapi-mkl}/mkl/latest/benchmarks/mp_linpack/xhpl_intel64_dynamic',
               use_mpi=True)

    # Redefine default bcast to 6 for the MKL-optimized case
    workload_variable('bcast',
                      default='6',
                      description='BCAST for Intel MKL optimized calculator',
                      workloads=['calculator'])

    # overload the inherited method to correct required_packages
    def _inject_required_builtins(self):
        # Do inherited stuff to inject the stuff coming from directives
        # above and in parent classes.
        super()._inject_required_builtins()

        # Now ensure that hpl is no longer required
        if 'hpl' in self.required_packages.keys():
            self.required_packages.pop('hpl')
