# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


class SetEnvVarMod(BasicModifier):
    """Define a modifier with only an environment variable modification using
    the set method"""
    name = "set-env-var-mod"

    tags('test')

    mode('test', description='This is a test mode')

    modifier_variable('mask_test', default='0x0', description='Test mask var',
                      modes=['test'], expandable=False)

    env_var_modification('test_var', modification='test_val', method='set', mode='test')
    env_var_modification('mask_env_var', modification='{mask_test}', method='set', mode='test')
