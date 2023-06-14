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
    variable_modification('log', '{experiment_run_dir}/gcp-metadata.log', method='set', modes=['standard'])
    archive_pattern('{log}')


    register_builtin('gcp_metadata_exec')

    def gcp_metadata_exec(self):
        #return ['lscpu >> {log}']
        machine_type = 'curl -w "\\n" "http://metadata.google.internal/computeMetadata/v1/instance/machine-type" -H "Metadata-Flavor: Google" >> {log}'

        image = 'curl -w "\\n" "http://metadata.google.internal/computeMetadata/v1/instance/image" -H "Metadata-Flavor: Google" >> {log}'

        gid = 'curl -w "=GID\\n" "http://metadata.google.internal/computeMetadata/v1/instance/id" -H "Metadata-Flavor: Google" >> {log}'

        ghostname = 'curl -w "\\n" "http://metadata.google.internal/computeMetadata/v1/instance/hostname" -H "Metadata-Flavor: Google" >> {log}'

        return [machine_type, image, gid, ghostname]

    figure_of_merit('machine-type', fom_regex=r'(?P<machine>.*machineTypes.*)', group_name='machine', log_file='{log}')
    figure_of_merit('image', fom_regex=r'(?P<image>.*global/images.*)', group_name='image', log_file='{log}')
    figure_of_merit('gid', fom_regex=r':(?P<gid>.*)=GID', group_name='gid', log_file='{log}')
    figure_of_merit('ghostname', fom_regex=r'(?P<ghostname>.*internal)', group_name='ghostname', log_file='{log}')
