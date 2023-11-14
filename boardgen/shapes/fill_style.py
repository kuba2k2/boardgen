# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from pydantic.color import Color
from svgwrite import Drawing
from svgwrite.gradients import LinearGradient
from svgwrite.mixins import Presentation

from ..utils import EvalFloat, Model
from ..vector import V
from .base import Shape


class FillStyle(Model):
    color: Color = None
    lgrad: tuple[V, Color, V, Color] = None
    width: EvalFloat = None

    def apply_to(
        self,
        dwg: Drawing,
        el: Presentation,
        shape: Shape,
        unit: float = 1.0,
        stroke: bool = False,
    ):
        color = None
        if self.color:
            color = self.color.as_hex()
        elif self.lgrad:
            units = max(*self.lgrad[0].tuple, *self.lgrad[2].tuple)
            if units <= 1:
                pos1 = shape.pos1
                size = shape.size
                for i in [0, 2]:
                    self.lgrad[i].x *= size.x
                    self.lgrad[i].y *= size.y
                    self.lgrad[i].x += pos1.x
                    self.lgrad[i].y += pos1.y
            grad = LinearGradient(
                start=(self.lgrad[0] * unit).tuple,
                end=(self.lgrad[2] * unit).tuple,
                gradientUnits="userSpaceOnUse",
            )
            grad.add_stop_color(offset="0%", color=self.lgrad[1])
            grad.add_stop_color(offset="100%", color=self.lgrad[3])
            color = grad
            dwg.add(grad)
        if color:
            if stroke:
                if not self.width:
                    raise ValueError("No stroke width")
                el.stroke(color=color, width=self.width * unit)
            else:
                el.fill(color=color)
