# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from svgwrite import Drawing
from svgwrite.shapes import Rect

from ...models.enums import IOType
from ...vector import V
from ..base import LabelShape


class IOLine(LabelShape):
    type: IOType
    padding: V = V(0.25, 0.25)

    def draw(self, dwg: Drawing, unit: float = 1.0):
        rect = Rect(
            insert=(self.pos1 * unit).tuple,
            size=(self.size * unit).tuple,
        )
        rect.fill(color=self.color.as_hex())
        dwg.add(rect)

    @property
    def height(self) -> float:
        return 0.1 * self.label_size
