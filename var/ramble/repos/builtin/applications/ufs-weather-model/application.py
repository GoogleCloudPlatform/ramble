# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *
from ramble.expander import Expander


class UfsWeatherModel(SpackApplication):
    '''Define FV3 application via ufs-weather-model'''
    name = 'ufs-weather-model'

    maintainers('dodecatheon')

    tags('nwp', 'weather')

    define_compiler('gcc9', spack_spec='gcc@9.3.0')

    software_spec('ompi415', spack_spec="openmpi@4.1.5", compiler='gcc9')

    software_spec('python39', spack_spec="python@3.9.15", compiler='gcc9')
    software_spec('esmf', spack_spec="esmf@8.0.1", compiler='gcc9')

    software_spec('ufs-weather-model',
                  spack_spec='ufs-weather-model@2.0.0 +avx2 +openmp', compiler='gcc9')

    required_package('ufs-weather-model')

    input_file('simple_test_case', url='https://ftp.emc.ncep.noaa.gov/EIB/UFS/simple-test-case.tar.gz',
               sha256='c713ecb208abcff9a7ec74d7991915d842f85a53b5771afa6b9c57c27651aaeb',
               description='Simple test case for ufs-weather-model')

    executable('execute', 'ufs_weather_model', use_mpi=True)

    executable('copy_input',
               template=['cp -pR {input_path}/* {experiment_run_dir}'], use_mpi=False)

    workload('simple_test_case', executables=['copy_input', 'execute'], input='simple_test_case')

    workload_variable('input_path', default='{simple_test_case}',
                      description='extracted simple-test-case tarfile path',
                      workloads=['simple_test_case'])

    log_str = os.path.join(Expander.expansion_str('experiment_run_dir'),
                           Expander.expansion_str('experiment_name') + '.out')

    figure_of_merit('Total wall clock time',
                    fom_regex=(r'^\s*The total amount of wall time\s+=\s+'
                               r'(?P<walltime>[0-9]+\.[0-9]+).*'),
                    group_name='walltime', log_file=log_str, units='s')

    figure_of_merit('Total user mode time',
                    fom_regex=(r'^\s*The total amount of time in user mode\s+=\s+'
                               r'(?P<usertime>[0-9]+\.[0-9]+).*'),
                    group_name='usertime', log_file=log_str, units='s')

    figure_of_merit('Total sys mode time',
                    fom_regex=(r'^\s*The total amount of time in sys mode\s+=\s+'
                               r'(?P<systime>[0-9]+\.[0-9]+).*'),
                    group_name='systime', log_file=log_str, units='s')

    figure_of_merit('Maximum resident set size',
                    fom_regex=(r'^\s*The maximum resident set size.*\s+=\s+'
                               r'(?P<res_set_size>[0-9]+).*'),
                    group_name='res_set_size', log_file=log_str, units='KB')

    figure_of_merit('Mean specific humidity above 75mb',
                    fom_regex=(r'^\s*Mean specific humidity.*=\s+'
                               r'(?P<mean_sp_hum>[0-9]+\.[0-9]+).*'),
                    group_name='mean_sp_hum', log_file=log_str, units='mg/kg')

    figure_of_merit('Total surface pressure',
                    fom_regex=(r'^\s*Total surface pressure.*=\s+'
                               r'(?P<tot_surf_press>[0-9]+\.[0-9]+).*'),
                    group_name='tot_surf_press', log_file=log_str, units='mb')

    figure_of_merit('mean dry surface pressure',
                    fom_regex=(r'^\s*mean dry surface pressure.*=\s+'
                               r'(?P<mean_dry_surf_press>'
                               r'[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*'
                               r').*'),
                    group_name='mean_dry_surf_press', log_file=log_str, units='mb')

    figure_of_merit('Total water vapor',
                    fom_regex=(r'^\s*Total Water Vapor.*=\s+'
                               r'(?P<tot_h2o_vapor>'
                               r'[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*'
                               r').*'),
                    group_name='tot_h2o_vapor', log_file=log_str, units='kg/m**2')

    figure_of_merit('Total cloud water',
                    fom_regex=(r'^\s*Total cloud water.*=\s+'
                               r'(?P<tot_cloud_h2o>'
                               r'[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*'
                               r').*'),
                    group_name='tot_cloud_h2o', log_file=log_str, units='kg/m**2')

    figure_of_merit('Total rain water',
                    fom_regex=(r'^\s*Total rain water.*=\s+'
                               r'(?P<tot_rain_h2o>'
                               r'[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*'
                               r').*'),
                    group_name='tot_rain_h2o', log_file=log_str, units='kg/m**2')

    figure_of_merit('Total snow',
                    fom_regex=(r'^\s*Total snow.*=\s+'
                               r'(?P<tot_snow>'
                               r'[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*'
                               r').*'),
                    group_name='tot_snow', log_file=log_str, units='kg/m**2')

    figure_of_merit('Total graupel',
                    fom_regex=(r'^\s*Total graupel.*=\s+'
                               r'(?P<tot_graupel>'
                               r'[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*'
                               r').*'),
                    group_name='tot_graupel', log_file=log_str, units='kg/m**2')

    success_criteria('program_ended', mode='string',
                     match=r'^\s+PROGRAM.*HAS ENDED\..*',
                     file=log_str)
