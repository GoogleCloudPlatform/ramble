# Copyright 2022-2026 Ramble a Series of LF projects, LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# The name of the Pygments (syntax highlighting) style to use.
# We use our own extension of the default style with a few modifications
from pygments.styles.default import DefaultStyle
from pygments.token import Generic


class RambleStyle(DefaultStyle):
    styles = DefaultStyle.styles.copy()
    background_color = "#f4f4f8"
    styles[Generic.Output] = "#355"
    styles[Generic.Prompt] = "bold #346ec9"
