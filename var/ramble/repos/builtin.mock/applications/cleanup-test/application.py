# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class CleanupTest(ExecutableApplication):
    name = "cleanup-test"

    executable(
        "check-file-existence",
        template=[
            '[ -f "pre-{file_to_check}" ] && echo "File pre-{file_to_check} exists."',
            '[ -f "post-{file_to_check}" ] && echo "File post-{file_to_check} exists."',
        ],
    )
    executable(
        "execute",
        template="mkdir -p subdir && touch file0.txt file1.log subdir/file2.log",
    )

    workload("test", executables=["check-file-existence", "execute"])

    cleanup(
        name="cleanup_pre",
        description="Remove pre_file.txt before main execution",
        regex=r".*pre-.*",
        pre=True,
        post=False,
    )

    cleanup(
        name="cleanup_all_log",
        description="Remove log files after execution",
        regex=r".*\.log",
        post=True,
        pre=False,
        recurse=True,
    )
