from typing import Annotated

from pydantic import StringConstraints

StrippedString = Annotated[
    str, 
    StringConstraints(strip_whitespace=True)
]
