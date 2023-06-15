# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from pydantic import Field
from svgwrite import Drawing, shapes

from ..utils import EvalFloat
from ..vector import V
from .base import Shape
from .fill_style import FillStyle


class Rect(Shape):
    size_v: V = Field(alias="size")
    rx: EvalFloat = None
    ry: EvalFloat = None
    fill: FillStyle = None
    stroke: FillStyle = None

    def draw(self, dwg: Drawing):
        if self.stroke and self.stroke.width:
            self.pos += (self.stroke.width / 2, self.stroke.width / 2)
            self.size_v -= (self.stroke.width, self.stroke.width)
        rect = shapes.Rect(
            insert=self.pos.tuple,
            size=self.size_v.tuple,
            rx=self.rx,
            ry=self.ry,
            id=self.fullid,
        )
        if self.fill:
            self.fill.apply_to(dwg, rect)
        if self.stroke:
            self.stroke.apply_to(dwg, rect, stroke=True)
        dwg.add(rect)

    @property
    def x2(self) -> float:
        return self.x1 + self.size_v.x

    @property
    def y2(self) -> float:
        return self.y1 + self.size_v.y
