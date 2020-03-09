# Some type definitions that can be useful.

try:
    # Python 3.8 and later
    from typing import Literal
except ImportError:
    from typing_extensions import Literal
