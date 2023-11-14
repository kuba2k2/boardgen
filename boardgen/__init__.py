# Copyright (c) Kuba Szczodrzyński 2022-05-11.

import os
import sys

while os.getcwd() in sys.path:
    sys.path.remove(os.getcwd())

from . import models, shapes, utils
from .core import Core
from .mixins import HasId, HasVars, ParentType
from .readme import ReadmeWriter
from .variant import VariantWriter
from .vector import V

__all__ = [
    "models",
    "shapes",
    "utils",
    "Core",
    "HasVars",
    "HasId",
    "ParentType",
    "V",
    "ReadmeWriter",
    "VariantWriter",
]
