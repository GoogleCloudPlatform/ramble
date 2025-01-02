# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
# SPDX-License-Identifier: (Apache-2.0 OR MIT)



GIT_ROOT=`git rev-parse --show-toplevel`

INSTALL_HOOKS="pre-commit"

SRC_DIR=${GIT_ROOT}/share/ramble/qa/git-hooks
HOOKS_DIR=${GIT_ROOT}/.git/hooks

echo "Installing git hooks from:"
echo "   ${SRC_DIR}"
echo "Into directory:"
echo "   ${HOOKS_DIR}"

for HOOK in ${INSTALL_HOOKS}
do
    cp ${SRC_DIR}/${HOOK} ${HOOKS_DIR}/${HOOK}
    chmod a+x ${HOOKS_DIR}/${HOOK}
done


