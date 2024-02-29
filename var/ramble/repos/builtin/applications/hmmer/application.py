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


class Hmmer(SpackApplication):
    '''HMMER is used for searching sequence databases for sequence homologs,
    and for making sequence alignments. It implements methods using
    probabilistic models called profile hidden Markov models (profile HMMs).

    It is often used with profile databases such as Pfam (for protein
    families), Rfam (for non-coded RNA families), Dfam (for repetitive
    DNA based), etc.

    Homepage: www.hmmer.org'''

    name = 'hmmer'

    maintainers('dodecatheon')

    tags('molecular-dynamics', 'hidden-markov-models', 'bio-molecule')

    define_compiler('gcc9', spack_spec='gcc@9.3.0')

    software_spec('impi_2018', spack_spec='intel-mpi@2018.4.274')

    software_spec('hmmer', spack_spec='hmmer@3.3.2', compiler='gcc9')

    # This would ideally not use the current_release, as the package will need to be manually updated per release
    # Here current_release == 'Pfam36.0'
    input_file('Pfam_A',
               url='http://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz',
               sha256='8779125bd2ed533886c559a5808903800f5c262798e5b086d276c2b829566b3a',
               description='The Pfam database is a large collection of protein families, ' +
               'each represented by multiple sequence alignments and hidden Markov models (HMMs).')

    input_file('uniprot_sprot_fasta',
               url='https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.fasta.gz',
               sha256='b0cacbf62fbf02f410dfd5e7963099762e53ed9f6fb123ba655583a9f7f0adab',
               description='Uniprot Swiss Prot fasta search input')

    executable('execute',
               'hmmsearch --mpi -o hmmsearch.out {database_path} {input_path}',
               use_mpi=True)

    executable('tail_hmmsearch_out',
               'tail -100 hmmsearch.out',
               use_mpi=False)

    workload('fasta_pfam', executables=['execute', 'tail_hmmsearch_out'],
             inputs=['Pfam_A', 'uniprot_sprot_fasta'])

    workload_variable('database_path', default='{Pfam_A}/Pfam-A.hmm',
                      description='Database path for Pfam-A',
                      workloads=['fasta_pfam'])

    workload_variable('input_path', default='{uniprot_sprot_fasta}/uniprot_sprot.fasta',
                      description='Input path for uniprot_sprot.fasta',
                      workloads=['fasta_pfam'])

    hmmsearch_out = os.path.join(Expander.expansion_str('experiment_run_dir'),
                                 'hmmsearch.out')

    out_file = os.path.join(Expander.expansion_str('experiment_run_dir'),
                            Expander.expansion_str('experiment_name') + '.out')

    figure_of_merit('Elapsed time',
                    fom_regex=r'# CPU.*Elapsed:\s+(?P<elapsed_time>[0-9]+:[0-9]+:[0-9]+\.*[0-9]*)\s*$',
                    group_name='elapsed_time', log_file=out_file, units='hms')

    figure_of_merit('Million dynamic programming cells per second',
                    fom_regex=r'^#\s*Mc/sec:\s+(?P<mc_per_sec>[0-9]+)\s*',
                    group_name='mc_per_sec', log_file=out_file, units='Mc/s')

    success_criteria('ok', mode='string', match=r'^\[ok\]$', file=out_file)
