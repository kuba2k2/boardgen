# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from svgwrite import Drawing

from ..mixins import HasVars, ParentType
from ..vector import V
from .base import Shape


class ShapeGroup(Shape, HasVars):
    name: str
    repeat: int = 1

    shapes: list[Shape] = []

    def __init__(self, core, parent: ParentType | None, *a, **kw):
        super().__init__(*a, **kw)

        if not self.name:  # used in wrap()
            return

        if isinstance(parent, HasVars):
            # apply parent variables
            vars = self.vars
            self.vars = dict(parent.vars)
            self.vars |= vars

        self.shapes = []
        self.vars["J"] = self.repeat
        for i in range(self.repeat):
            self.vars["I"] = i
            self.shapes += core.build_shapes(self.name, self, self.pos)
        self.vars.pop("I", None)
        self.vars.pop("J", None)

    def draw(self, dwg: Drawing):
        for shape in self.shapes:
            shape.draw(dwg)

    def get_by_id(self, id: str) -> Shape | None:
        for shape in self.shapes:
            if shape.fullid == id:
                return shape
            if isinstance(shape, ShapeGroup):
                result = shape.get_by_id(id)
                if result:
                    return result
        return None

    def get_by_id_path(self, path: str) -> Shape | None:
        path = path.split(".")
        id = path[0]
        for shape in self.shapes:
            if shape.base_id != id:
                continue
            if len(path) == 1:
                return shape
            if isinstance(shape, ShapeGroup):
                return shape.get_by_id_path(".".join(path[1:]))
            return shape
        return None

    @staticmethod
    def wrap(core, id: str, shapes: list[Shape]) -> "ShapeGroup":
        return ShapeGroup(
            core=core,
            parent=None,
            id=id,
            pos=V(0.0, 0.0),
            name="",
            shapes=shapes,
        )

    def move(self, vec: V):
        self.pos += vec
        for shape in self.shapes:
            shape.move(vec)

    @property
    def x1(self) -> float:
        return min(self.shapes, key=lambda t: t.x1).x1

    @property
    def y1(self) -> float:
        return min(self.shapes, key=lambda t: t.y1).y1

    @property
    def x2(self) -> float:
        return max(self.shapes, key=lambda t: t.x2).x2

    @property
    def y2(self) -> float:
        return max(self.shapes, key=lambda t: t.y2).y2
