# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import llnl.util.tty as tty

from ramble.application import ApplicationBase, ApplicationError
import ramble.spack_runner

header_color = '@*b'
level1_color = '@*g'
plain_format = '@.'


def section_title(s):
    return header_color + s + plain_format


def subsection_title(s):
    return level1_color + s + plain_format


class SpackApplication(ApplicationBase):
    """Specialized class for applications that are installed from spack.

    This class can be used to set up an application that will be installed
    via spack.

    It currently only utilizes phases defined in the base class.
    """

    uses_spack = True
    _spec_groups = [('default_compilers', 'Default Compilers'),
                    ('mpi_libraries', 'MPI Libraries'),
                    ('software_specs', 'Software Specs')]
    _spec_keys = ['base', 'version', 'variants',
                  'dependenices', 'target', 'arch'
                  'compiler', 'mpi']

    def __init__(self, file_path):
        super().__init__(file_path)
        self._setup_phases = [
            'create_spack_env',
            'install_software',
            'get_inputs',
            'make_experiments'
        ]

        self._analyze_phases = ['analyze_experiments']
        self._archive_phases = ['archive_experiments']
        self._mirror_phases = [
            'mirror_inputs',
            'create_spack_env',
            'mirror_software'
        ]

        self.application_class = 'SpackApplication'

    def _long_print(self):
        out_str = super()._long_print()

        for group in self._spec_groups:
            if hasattr(self, group[0]):
                out_str.append('\n')
                out_str.append(section_title('%s:\n' % group[1]))
                for name, info in getattr(self, group[0]).items():
                    out_str.append(subsection_title('  %s:\n' % name))
                    for key in self._spec_keys:
                        if key in info and info[key]:
                            out_str.append('    %s = %s\n' % (key,
                                                              info[key]))

        return ''.join(out_str)

    def _add_expand_vars(self, expander):
        super()._add_expand_vars(expander)
        try:
            runner = ramble.spack_runner.SpackRunner()

            runner.create_env(expander.expand_var('{spack_env}'))
            runner.activate()
            runner_vars = runner.generate_expand_vars(expander,
                                                      self.software_specs)
            expander.set_var('spack_setup', runner_vars, 'experiment')

        except ramble.spack_runner.RunnerError as e:
            tty.die(e)

    def _extract_specs(self, workspace, expander, spec_name, app_name):
        """Build a list of all specs which the named spec requires

        Traverse a spec and all of its dependencies to extract a list
        of specs
        """
        spec_list = []
        spec = workspace.get_named_spec(spec_name, app_name)
        if 'dependencies' in spec:
            for dep in spec['dependencies']:
                spec_list.extend(
                    self._extract_specs(workspace,
                                        expander,
                                        dep, app_name))
        spec['application_name'] = app_name
        spec_list.append((spec_name, spec))
        return spec_list

    def _create_spack_env(self, workspace, expander):
        """Create the spack environment for this experiment

        Extract all specs this experiment uses, and write the spack environment
        file for it.
        """

        # See if we cached this already, and if so return
        namespace = expander.spec_namespace
        if not namespace:
            raise ApplicationError('Ramble spec_namespace is set to None.')

        cache_tupl = ('spack-env', namespace)
        if workspace.check_cache(cache_tupl):
            tty.debug('{} already in cache.'.format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            runner = ramble.spack_runner.SpackRunner(dry_run=workspace.dry_run)

            runner.create_env(expander.expand_var('{spack_env}'))

            # Write auxiliary software files into created spack env.
            for name, contents in workspace.all_auxiliary_software_files():
                aux_file_path = expander.expand_var(os.path.join('{spack_env}', f'{name}'))
                runner.add_include_file(aux_file_path)
                with open(aux_file_path, 'w+') as f:
                    f.write(expander.expand_var(contents))

            runner.activate()

            added_specs = {}
            mpi_added = {}

            app_context = expander.expand_var('{spec_name}')
            for name, spec_info in \
                    workspace.all_application_specs(app_context):

                if 'mpi' in spec_info and \
                        spec_info['mpi'] not in mpi_added:
                    mpi_spec = workspace.get_named_spec(spec_info['mpi'],
                                                        'mpi_library')
                    mpi_added[spec_info['mpi']] = True
                    runner.add_spec(
                        expander.expand_var(workspace.spec_string(mpi_spec,
                                            use_custom_specifier=True))
                    )

                pkg_specs = self._extract_specs(workspace, expander, name,
                                                app_context)
                for pkg_name, pkg_info in pkg_specs:
                    if pkg_name not in added_specs:
                        added_specs[pkg_name] = True

                        spec_str = workspace.spec_string(pkg_info,
                                                         as_dep=False)

                        runner.add_spec(expander.expand_var(spec_str))

                if name not in added_specs:
                    added_specs[name] = True
                    spec_str = workspace.spec_string(spec_info,
                                                     as_dep=False)

                    runner.add_spec(expander.expand_var(spec_str))

            for name, spec_info in self.software_specs.items():
                if 'required' in spec_info and spec_info['required']:
                    if name not in added_specs:
                        tty.die('Required spec %s is not ' % name +
                                'defined in ramble.yaml')

            runner.concretize()

        except ramble.spack_runner.RunnerError as e:
            tty.die(e)

    def _install_software(self, workspace, expander):
        """Install application's software using spack"""

        # See if we cached this already, and if so return
        namespace = expander.spec_namespace
        if not namespace:
            raise ApplicationError('Ramble spec_namespace is set to None.')

        cache_tupl = ('spack-install', namespace)
        if workspace.check_cache(cache_tupl):
            tty.debug('{} already in cache.'.format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            runner = ramble.spack_runner.SpackRunner(dry_run=workspace.dry_run)
            runner.set_env(expander.expand_var('{spack_env}'))

            runner.activate()
            runner.install()

            app_context = expander.expand_var('{spec_name}')
            for name, spec_info in \
                    workspace.all_application_specs(app_context):
                if 'mpi' in spec_info:
                    mpi_spec = workspace.get_named_spec(spec_info['mpi'],
                                                        'mpi_library')
                    spec_str = workspace.spec_string(mpi_spec)
                    package_path = runner.get_package_path(spec_str)
                    expander.set_package_path(name, package_path)

                pkg_specs = self._extract_specs(workspace, expander, name,
                                                app_context)
                for pkg_name, pkg_info in pkg_specs:
                    spec = workspace._build_spec_dict(pkg_info,
                                                      app_name=app_context)
                    spec_str = workspace.spec_string(spec,
                                                     as_dep=False)
                    package_path = runner.get_package_path(spec_str)
                    expander.set_package_path(pkg_name, package_path)

        except ramble.spack_runner.RunnerError as e:
            tty.die(e)

    def _mirror_software(self, workspace, expander):
        """Mirror software source for this experiment using spack"""
        import re

        # See if we cached this already, and if so return
        namespace = expander.spec_namespace
        if not namespace:
            raise ApplicationError('Ramble spec_namespace is set to None.')

        cache_tupl = ('spack-mirror', namespace)
        if workspace.check_cache(cache_tupl):
            tty.debug('{} already in cache.'.format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            runner = ramble.spack_runner.SpackRunner(dry_run=workspace.dry_run)
            runner.set_env(expander.expand_var('{spack_env}'))

            runner.activate()

            mirror_output = runner.mirror_environment(workspace._software_mirror_path)

            present = 0
            added = 0
            failed = 0

            present_regex = re.compile(r'\s+(?P<num>[0-9]+)\s+already present')
            present_match = present_regex.search(mirror_output)
            if present_match:
                present = int(present_match.group('num'))

            added_regex = re.compile(r'\s+(?P<num>[0-9]+)\s+added')
            added_match = added_regex.search(mirror_output)
            if added_match:
                added = int(added_match.group('num'))

            failed_regex = re.compile(r'\s+(?P<num>[0-9]+)\s+failed to fetch.')
            failed_match = failed_regex.search(mirror_output)
            if failed_match:
                failed = int(failed_match.group('num'))

            added_start = len(workspace._software_mirror_stats.new)
            for i in range(added_start, added_start + added):
                workspace._software_mirror_stats.new[i] = i

            present_start = len(workspace._software_mirror_stats.present)
            for i in range(present_start, present_start + present):
                workspace._software_mirror_stats.present[i] = i

            error_start = len(workspace._software_mirror_stats.errors)
            for i in range(error_start, error_start + failed):
                workspace._software_mirror_stats.errors.add(i)

        except ramble.spack_runner.RunnerError as e:
            tty.die(e)
