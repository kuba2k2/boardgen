# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from pydantic.color import Color
from svgwrite import Drawing
from svgwrite.gradients import LinearGradient
from svgwrite.mixins import Presentation

from ..utils import Model
from ..vector import V


class FillStyle(Model):
    color: Color = None
    lgrad: tuple[V, Color, V, Color] = None
    width: float = None

    def apply_to(self, dwg: Drawing, el: Presentation, stroke: bool = False):
        color = None
        if self.color:
            color = self.color.as_hex()
        elif self.lgrad:
            unit = max(*self.lgrad[0].tuple, *self.lgrad[2].tuple)
            grad = LinearGradient(
                start=self.lgrad[0].tuple,
                end=self.lgrad[2].tuple,
                gradientUnits="userSpaceOnUse" if unit > 1 else "objectBoundingBox",
            )
            grad.add_stop_color(offset="0%", color=self.lgrad[1])
            grad.add_stop_color(offset="100%", color=self.lgrad[3])
            color = grad
            dwg.add(grad)
        if color:
            if stroke:
                if not self.width:
                    raise ValueError("No stroke width")
                el.stroke(color=color, width=self.width)
            else:
                el.fill(color=color)
