# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import ramble.cmd.common.arguments as arguments

import ramble.reports
from ramble.util.logger import logger


description = "create a report of Ramble experiment results"
section = "report"
level = "short"


def setup_parser(subparser):
    subparser.add_argument(
        '--workspace', dest='workspace',
        metavar='WRKSPC',
        action='store',
        help='the workspace to report on'
    )

    subparser.add_argument(
        '--strong-scaling', dest='strong_scaling',
        nargs='+',
        action='append',
        help='generate a scaling report, requires two args: [performance metric] [scaling metric] [optional: group by]',
        required=False
    )

    subparser.add_argument(
        '--weak-scaling', dest='weak_scaling',
        nargs='+',
        action='append',
        help='generate a scaling report, requires two args: [performance metric] [scaling metric] [optional: group by]',
        required=False
    )

    subparser.add_argument(
        '--compare', dest='compare',
        nargs='+',
        action='append',
        help='generate a comparison report, requires at least two args: [FOM 1] [Additional FOMs] [optional: group by(s)]',
        required=False
    )

    subparser.add_argument(
        '--foms', dest='foms',
        action='store_true',
        help='generate a FOM report, showing values of FOMs for each experiment',
        required=False
    )

    subparser.add_argument(
        '-n', '--normalize', dest='normalize',
        action='store_true',
        help='Normalize charts where possible. For scaling charts, this requires fom_type to be specified as either "time" or "throughput".',
        required=False
    )

    arguments.add_common_arguments(subparser, ['where', 'exclude_where', 'filter_tags'])



def report(parser, args):
    # first, check if --workspace flag 
    
    print(args.workspace)
    
    if args.workspace:
        print(args.workspace)
    
    #ws = ramble.cmd.require_active_workspace(cmd_name='on')

    ws = get_workspace(args.workspace)
    

    ramble.reports.make_report(ws, args)
