# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

#
# This script tests that Ramble's tab completion scripts work.
#
# The tests are portable to bash, zsh, and bourne shell, and can be run
# in any of these shells.
#

export QA_DIR=$(dirname "$0")
export SHARE_DIR=$(cd "$QA_DIR/.." && pwd)
export RAMBLE_ROOT=$(cd "$QA_DIR/../../.." && pwd)

. "$QA_DIR/test-framework.sh"

# Fail on undefined variables
set -u

# Source setup-env.sh before tests
. "$SHARE_DIR/setup-env.sh"
. "$SHARE_DIR/ramble-completion.$_rmb_shell"

title "Testing ramble-completion.$_rmb_shell with $_rmb_shell"

# Ramble command is now available
succeeds which ramble

title 'Testing all subcommands'
while IFS= read -r line
do
    # Test that completion with no args works
    succeeds _ramble_completions ${line[*]} ''

    # Test that completion with flags works
    contains '-h --help' _ramble_completions ${line[*]} -
done <<- EOF
    $(ramble commands --aliases --format=subcommands)
EOF

title 'Testing for correct output'
contains 'list' _ramble_completions ramble  ''
contains 'workspace' _ramble_completions ramble work
contains 'hostname' _ramble_completions ramble list host

# XFAIL: Fails for Python 2.6 because pkg_resources not found?
#contains 'compilers.py' _ramble_completions ramble unit-test ''

title 'Testing debugging functions'

# This is a particularly tricky case that involves the following situation:
#     `ramble -d [] list `
# Here, [] represents the cursor, which is in the middle of the line.
# We should tab-complete optional flags for `ramble`, not optional flags for
# `ramble list` or application names.
COMP_LINE='ramble -d  list '
COMP_POINT=10
COMP_WORDS=(ramble -d list)
COMP_CWORD=2
COMP_KEY=10
COMP_TYPE=64

_bash_completion_ramble
contains "--all-help" echo "${COMPREPLY[@]}"

contains "['ramble', '-d', 'list', '']" _pretty_print COMP_WORDS[@]

# Set the rest of the intermediate variables manually
COMP_WORDS_NO_FLAGS=(ramble list)
COMP_CWORD_NO_FLAGS=1
subfunction=_ramble
cur=

list_options=true
contains "'True'" _test_vars
list_options=false
contains "'False'" _test_vars
