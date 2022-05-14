# Copyright (c) Kuba Szczodrzyński 2022-05-11.

from pydantic.color import Color

from ..utils import Model


class Role(Model):
    title: str
    color: Color
    ratio: float = 1.8
