# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

import functools

from toolz import valfilter

from .settings import Settings, Dependency

__all__ = ["ignore_nones", "Settings", "Dependency"]


def ignore_nones(fn):
    """Decorator which calls `fn` with `*args, **kwargs`, but pops all items of
    `kwargs`, which are `None` (`foo(bar=None)` becomes `foo()`).

    This is useful when using boto3, since it often doesn't allow passing
    `None` as a not-specified value.

    ::

        @ignore_nones
        def foo(bar=42):
            return bar

        assert foo(None) == 42
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        kwargs = valfilter(lambda val: val is not None, kwargs)
        return fn(*args, **kwargs)

    return wrapper
