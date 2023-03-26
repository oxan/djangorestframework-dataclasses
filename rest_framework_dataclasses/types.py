from __future__ import annotations

import sys
from dataclasses import Field
from typing import Any, ClassVar, Dict

# Alias these types into this module for ease of use elsewhere.
if sys.version_info >= (3, 8):
    from typing import Final, Literal, Protocol
else:
    from typing_extensions import Final, Literal, Protocol


# As dataclasses don't have a baseclass, we typehint them using a protocol matching the injected `__dataclass_fields__`
# attribute. This is also what the Python stdlib typeshed does:
# https://github.com/python/typeshed/blob/ced150a7e8edafe98ffceb3365fe66f800bc6780/stdlib/_typeshed/__init__.pyi#L309-L314
# Requires MyPy 0.990+
class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field[Any]]]
