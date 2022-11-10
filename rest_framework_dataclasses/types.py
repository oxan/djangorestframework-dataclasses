# Some type definitions that can be useful.

from typing import ClassVar, Dict, Union

try:
    # Python 3.8 and later
    from typing import Final, Literal, Protocol
except ImportError:
    from typing_extensions import Final, Literal, Protocol


# As dataclasses don't have a baseclass, we typehint them using a protocol matching the injected `__dataclass_fields__`
# attribute. Mypy 0.990 changed the attribute from an instance variable to a ClassVar, so use an union for compatibility
# with both older and newer versions. For reference, see https://stackoverflow.com/a/55240861 and
# https://github.com/python/mypy/issues/14029.
class NewStyleDataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[dict]

class OldStyleDataclassProtocol(Protocol):
    __dataclass_fields__: dict

Dataclass = Union[OldStyleDataclassProtocol, NewStyleDataclassProtocol]
