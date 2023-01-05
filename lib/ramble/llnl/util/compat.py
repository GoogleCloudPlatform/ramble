# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
# isort: off

import sys

if sys.version_info < (3,):
    from itertools import ifilter as filter
    from itertools import imap as map
    from itertools import izip as zip
    from itertools import izip_longest as zip_longest  # novm
    from urllib import urlencode as urlencode
    from urllib import urlopen as urlopen
else:
    filter = filter
    map = map
    zip = zip
    from itertools import zip_longest as zip_longest  # novm # noqa: F401
    from urllib.parse import urlencode as urlencode   # novm # noqa: F401
    from urllib.request import urlopen as urlopen     # novm # noqa: F401

if sys.version_info >= (3, 3):
    from collections.abc import Hashable as Hashable                # novm
    from collections.abc import Iterable as Iterable                # novm
    from collections.abc import Mapping as Mapping                  # novm
    from collections.abc import MutableMapping as MutableMapping    # novm
    from collections.abc import MutableSequence as MutableSequence  # novm
    from collections.abc import MutableSet as MutableSet            # novm
    from collections.abc import Sequence as Sequence                # novm
else:
    from collections import Hashable as Hashable                # noqa: F401
    from collections import Iterable as Iterable                # noqa: F401
    from collections import Mapping as Mapping                  # noqa: F401
    from collections import MutableMapping as MutableMapping    # noqa: F401
    from collections import MutableSequence as MutableSequence  # noqa: F401
    from collections import MutableSet as MutableSet            # noqa: F401
    from collections import Sequence as Sequence                # noqa: F401
