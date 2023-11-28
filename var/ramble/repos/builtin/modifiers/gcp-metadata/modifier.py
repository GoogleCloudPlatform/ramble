# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


class GcpMetadata(BasicModifier):
    """Define a modifier to grab GCP VM metadata

    This mod can capture usefull metadata (such as node type and VM image) for
    GCP VMs
    """

    name = "GcpMetadata"

    tags('gcp-metadata')
    maintainers('rfbgo')

    mode('standard', description='Standard execution mode')
    default_mode('standard')

    executable_modifier('gcp_metadata_exec')

    def gcp_metadata_exec(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable
        post_cmds = []
        pre_cmds = []

        payloads = [
            # end point, use_mpi
            ('machine-type', False),
            ('image', False),
            ('hostname', False),
            ('id', True),  # True since we want the gid of every node
        ]

        rm_template = []
        for end_point, _ in payloads:
            rm_template.append(f'rm "{{experiment_run_dir}}/gcp-metadata.{end_point}.log"')

        pre_cmds.append(
            CommandExecutable('file-rm',
                              template=rm_template,
                              mpi=False,
                              )
        )

        for end_point, use_mpi in payloads:
            pre_cmds.append(
                CommandExecutable('machine-type',
                                  template=[
                                      f'curl -s -w "\\n" "http://metadata.google.internal/computeMetadata/v1/instance/{end_point}" -H "Metadata-Flavor: Google"'
                                  ],
                                  mpi=use_mpi,
                                  redirect=f'{{experiment_run_dir}}/gcp-metadata.{end_point}.log')
            )

        return pre_cmds, post_cmds

    def _prepare_analysis(self, workspace):
        import os.path
        ids = set()
        file_name = self.expander.expand_var('{experiment_run_dir}/gcp-metadata.id.log')

        if os.path.isfile(file_name):
            with open(file_name, 'r') as f:
                for cur_id in f.readlines():
                    ids.add(cur_id.strip())

            with open(self.expander.expand_var('{experiment_run_dir}/gcp-metadata.id_list.log'), 'w+') as f:
                f.write(", ".join(sorted(ids)))

    figure_of_merit('machine-type', fom_regex=r'.*machineTypes/(?P<machine>.*)', group_name='machine', log_file='{experiment_run_dir}/gcp-metadata.machine-type.log')
    figure_of_merit('image', fom_regex=r'(?P<image>.*global/images.*)', group_name='image', log_file='{experiment_run_dir}/gcp-metadata.image.log')

    # This is intentionally left singular, to get the hostname of the "parent" or "root" process
    figure_of_merit('ghostname', fom_regex=r'(?P<ghostname>.*internal)', group_name='ghostname', log_file='{experiment_run_dir}/gcp-metadata.hostname.log')

    # This returns a list of all known gids in the job
    figure_of_merit('gids', fom_regex=r'(?P<gid>.*)', group_name='gid', log_file='{experiment_run_dir}/gcp-metadata.id_list.log')
