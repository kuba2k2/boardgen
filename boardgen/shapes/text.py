# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from svgwrite import Drawing, text

from .base import Shape
from .fill_style import FillStyle


class Text(Shape):
    text: str
    font_size: float
    fill: FillStyle = None

    def draw(self, dwg: Drawing):
        txt = text.Text(
            text=self.text,
            insert=self.pos.tuple,
            id=self.fullid,
            font_family="Consolas",
            font_size=self.font_size,
        )
        if self.fill:
            self.fill.apply_to(dwg, txt)
        dwg.add(txt)

    @property
    def x1(self) -> float:
        return self.pos.x - 1

    @property
    def y1(self) -> float:
        return self.pos.y - 1

    @property
    def x2(self) -> float:
        return self.pos.x + 1

    @property
    def y2(self) -> float:
        return self.pos.y + 1
