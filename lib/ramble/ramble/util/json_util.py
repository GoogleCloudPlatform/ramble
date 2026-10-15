# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import json
from typing import IO, Any, Dict, Optional

# This matches the spack_json format
dump_args: Dict[str, Any] = {"indent": 2, "separators": (",", ": ")}


def dump(obj: Any, fp: Optional[IO[str]] = None, **kwargs: Any) -> Optional[str]:
    """Wrapper around json.dump. If fp is None, returns the JSON as a string."""
    args = {**dump_args, **kwargs}
    if fp is None:
        return json.dumps(obj, **args)
    json.dump(obj, fp, **args)
    return None


def dumps(obj: Any, **kwargs: Any) -> str:
    """Wrapper around json.dumps using Ramble's default formatting arguments"""
    args = {**dump_args, **kwargs}
    return json.dumps(obj, **args)


def load(fp: IO[str], **kwargs: Any) -> Any:
    """Wrapper around json.load"""
    return json.load(fp, **kwargs)


def loads(s: str, **kwargs: Any) -> Any:
    """Wrapper around json.loads"""
    return json.loads(s, **kwargs)
