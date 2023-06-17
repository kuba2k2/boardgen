# Copyright (c) Kuba Szczodrzyński 2022-05-11.

import json
from copy import deepcopy
from typing import Any

from pydantic.color import Color
from svgwrite import Drawing

from ..mixins import HasId, HasVars
from ..models.enums import LabelDir, RoleType, ShapeType
from ..utils import EvalFloat, Model, splitxy, var
from ..vector import V


def remap(shape: dict):
    tuples = ["pos", "size"]
    for tpl in tuples:
        if tpl in shape:
            shape[tpl] = splitxy(shape[tpl])
    if "fill" in shape:
        if "lgrad" in shape["fill"]:
            shape["fill"]["lgrad"][0] = splitxy(shape["fill"]["lgrad"][0])
            shape["fill"]["lgrad"][2] = splitxy(shape["fill"]["lgrad"][2])
    return shape


class Shape(Model, HasId):
    base_id: str = None
    pos: V

    # for pad labels
    label_dir: LabelDir = None
    label_size: EvalFloat = None

    def draw(self, dwg: Drawing):
        raise NotImplementedError()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__post_init__()

    def __post_init__(self) -> None:
        pass

    @staticmethod
    def deserialize(
        core,
        parent: HasId | HasVars | Any,
        data: dict,
        # offset: tuple[float, float] = None,
    ) -> "Shape":
        # do not modify source object
        data = deepcopy(data)
        # allow includes without specified type
        if "type" not in data and "name" in data:
            data["type"] = "include"

        # prepend id with parent id path
        if isinstance(parent, HasId):
            if parent.fullid and "id" in data:
                data["base_id"] = data["id"]
                data["id"] = parent.fullid + "." + data["id"]

        # merge parent and child vars
        vars = {}
        if isinstance(parent, HasVars):
            vars |= dict(parent.vars)
        if "vars" in data:
            vars |= data["vars"]

        if vars:
            # ugly way to replace all vars in input JSON
            data = json.dumps(data)
            data = var(data, vars)
            data = json.loads(data)
            # build presets with current object's vars
            presets = core.build_presets(vars)
        else:
            # presets without vars
            presets = core.presets

        # apply shape preset(s)
        if "preset" in data:
            data |= presets[data["preset"]]
        if "presets" in data:
            for preset in data["presets"]:
                data |= presets[preset]

        # remap strings to tuples, etc.
        data = remap(data)

        shape_type = ShapeType(data["type"])
        ctor = core.shape_ctors[shape_type]
        ctor.update_forward_refs()
        return ctor(
            **data,
            core=core,
            parent=parent,
        )

    def move(self, vec: V):
        self.pos += vec

    @property
    def anchor(self) -> V:
        return self.pos

    @property
    def pos1(self) -> V:
        return V(self.x1, self.y1)

    @property
    def pos2(self) -> V:
        return V(self.x2, self.y2)

    @property
    def size(self) -> V:
        return V(self.width, self.height)

    @property
    def center(self) -> V:
        return self.pos1 + self.size / 2

    @property
    def x1(self) -> float:
        return self.pos.x

    @property
    def y1(self) -> float:
        return self.pos.y

    @property
    def x2(self) -> float:
        raise NotImplementedError()

    @property
    def y2(self) -> float:
        raise NotImplementedError()

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


class LabelShape(Shape):
    role_type: RoleType
    padding: V = V(0.05, 0.1)
    ratio: float
    color: Color

    def __post_init__(self) -> None:
        if self.label_size:
            self.padding *= self.label_size

    @property
    def dirv(self):
        return -1 if self.label_dir == LabelDir.LEFT else 1

    @property
    def width(self) -> float:
        return (self.label_size * self.ratio) - self.padding.x * 2

    @property
    def height(self) -> float:
        return self.label_size - self.padding.y * 2

    @property
    def x1(self) -> float:
        whalf = (self.label_size * self.ratio) / 2
        # whalf = (self.width) / 2
        return self.pos.x + whalf * (self.dirv - 1) + self.padding.x

    @property
    def x2(self) -> float:
        return self.x1 + self.width

    @property
    def y1(self) -> float:
        return self.pos.y - self.height / 2

    @property
    def y2(self) -> float:
        return self.y1 + self.height
