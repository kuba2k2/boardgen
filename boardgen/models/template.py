# Copyright (c) Kuba Szczodrzyński 2022-05-11.

from ..mixins import HasId, HasVars
from ..utils import Model


class Template(Model, HasId, HasVars):
    title: str
    width: float
    height: float
    front: list[dict]
    back: list[dict] = {}
    pads: dict[str, str] = {}
    test_pads: dict[str, str] = {}

    type: str = "include"
    pos = "0,0"
