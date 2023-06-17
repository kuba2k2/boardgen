# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from math import radians, tan

from svgwrite import Drawing
from svgwrite.container import Group
from svgwrite.shapes import Rect
from svgwrite.text import Text

from ...utils import EvalFloat
from ...vector import V
from ..base import LabelShape


class Block(LabelShape):
    text: str
    padding: V = V(0.05, 0.1)
    radius: EvalFloat = 0.3
    angle: EvalFloat = 15

    def draw(self, dwg: Drawing):
        g = Group()
        bg = Rect(
            insert=(0, 0),
            size=self.size.tuple,
            rx=self.radius,
            ry=self.radius,
        )
        bg.fill(color=self.color.as_hex())
        bg.skewX(-self.angle)
        skew_len = self.height * tan(radians(self.angle))
        g.add(bg)
        g.translate(self.x1 + skew_len / 2, self.y1)
        dwg.add(g)

        text = self.text
        text_pos = self.center
        text_color = "#423F42" if self.color.as_hsl_tuple()[2] > 0.5 else "white"

        if text.startswith("^"):
            text = text[1:]
            negation_line = Text(
                text="___",
                insert=(text_pos.x, self.y1 - self.width / 16),
                font_family="Consolas",
                font_size=self.label_size * 0.6,
                text_anchor="middle",
                dominant_baseline="middle",
            )
            negation_line.fill(color=text_color)
            dwg.add(negation_line)
            text_pos.y += self.width / 32

        txt = Text(
            text=text,
            insert=text_pos.tuple,
            font_family="Consolas",
            font_size=self.label_size * 0.6,
            text_anchor="middle",
            dominant_baseline="central",
        )
        txt.fill(color=text_color)
        dwg.add(txt)
