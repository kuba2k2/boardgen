# Copyright (c) Kuba Szczodrzyński 2022-05-11.

from svgwrite import Drawing

from ..mixins import HasId, HasVars
from ..shapes import Shape, ShapeGroup
from ..utils import Model
from ..vector import V
from .enums import RoleType, Side

PinDict = dict[RoleType, list[str] | str | int | float | None]


class Pcb(Model, HasId, HasVars):
    symbol: str
    templates: list[str]
    scale: float = 0
    ic: dict[int, PinDict] = {}
    front: list[dict] = []
    back: list[dict] = []
    pads: dict[str, str] = {}
    test_pads: dict[str, str] = {}
    pinout: dict[str, PinDict] = {}
    pinout_hidden: str = ""

    shapes: dict[Side, ShapeGroup] = {}

    def get_pos(self, side: Side) -> tuple[V, V]:
        shape = self.shapes[side]
        return (shape.pos1, shape.pos2)

    def get_size(self, side: Side) -> V:
        shape = self.shapes[side]
        return V(shape.width, shape.height)

    def draw(self, dwg: Drawing, side: Side, pos: V):
        shape = self.shapes[side]
        shape.move(pos)
        shape.draw(dwg)
        shape.move(-pos)

    def pad_by_id(self, id: str) -> Shape:
        for side in self.shapes.values():
            shape = side.get_by_id(id)
            if shape:
                return shape
        return None
