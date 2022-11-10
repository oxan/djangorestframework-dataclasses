# Some type definitions that can be useful.

from typing import Dict, ClassVar, Union

try:
    # Python 3.8 and later
    from typing import Final, Literal, Protocol
except ImportError:
    from typing_extensions import Final, Literal, Protocol


# for mypy 0.990+
class NewStyleDataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict]

# for mypy <0.990
class OldStyleDataclassProtocol(Protocol):
    __dataclass_fields__: Dict

Dataclass = Union[OldStyleDataclassProtocol, NewStyleDataclassProtocol]
