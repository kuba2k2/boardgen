# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from svgwrite import Drawing, shapes

from .base import Shape
from .fill_style import FillStyle


class Circle(Shape):
    r: float = None
    d: float = None
    fill: FillStyle = None
    stroke: FillStyle = None

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        if not self.r and not self.d:
            raise ValueError("No radius or diameter")
        if self.d:
            self.r = self.d / 2

    def draw(self, dwg: Drawing):
        circle = shapes.Circle(
            center=self.pos.tuple,
            r=self.r,
            id=self.fullid,
        )
        if self.fill:
            self.fill.apply_to(dwg, circle)
        if self.stroke:
            self.stroke.apply_to(dwg, circle, stroke=True)
        dwg.add(circle)

    @property
    def x1(self) -> float:
        return self.pos.x - self.r

    @property
    def y1(self) -> float:
        return self.pos.y - self.r

    @property
    def x2(self) -> float:
        return self.pos.x + self.r

    @property
    def y2(self) -> float:
        return self.pos.y + self.r
