from __future__ import annotations

import sys
from typing import Any, ClassVar, Dict, Union

# Alias these types into this module for ease of use elsewhere.
if sys.version_info >= (3, 8):
    from typing import Final, Literal, Protocol
else:
    from typing_extensions import Final, Literal, Protocol


# As dataclasses don't have a baseclass, we typehint them using a protocol matching the injected `__dataclass_fields__`
# attribute. Mypy 0.990 changed the attribute from an instance variable to a ClassVar, so use an union for compatibility
# with both older and newer versions. For reference, see https://stackoverflow.com/a/55240861 and
# https://github.com/python/mypy/issues/14029.
class NewStyleDataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Any]]


class OldStyleDataclassProtocol(Protocol):
    __dataclass_fields__: Dict[str, Any]


Dataclass = Union[OldStyleDataclassProtocol, NewStyleDataclassProtocol]
