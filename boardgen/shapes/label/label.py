# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from svgwrite import Drawing

from ...models.enums import IOType, RoleType, RoleValue
from ...models.role import Role
from ...shapes.base import Shape
from ...vector import V
from ..base import LabelShape
from .block import Block
from .io_line import IOLine


class Label(LabelShape):
    roles: dict[RoleType, RoleValue]
    labels: list[LabelShape] = []

    def build(
        self,
        core,
        pin: str,
        pad: Shape,
        hidden: list[str],
        block_extra: dict = {},
        io_extra: dict = {},
    ):
        # not connected pin
        if RoleType.NC in self.roles:
            self.roles[RoleType.IO] = IOType.NC.value
        # PWM pin
        if RoleType.PWM in self.roles:
            self.roles[RoleType.IO] = IOType.PWM.value
        # GPIO pin - set I/O role
        if RoleType.GPIO in self.roles and RoleType.IO not in self.roles:
            self.roles[RoleType.IO] = IOType.IO.value
        # power or ground pin
        if RoleType.PWR in self.roles or RoleType.GND in self.roles:
            self.roles[RoleType.IO] = IOType.PWR.value
        # ground text
        if RoleType.GND in self.roles:
            self.roles[RoleType.GND] = "GND"
        # no IO role
        if RoleType.IO not in self.roles:
            self.roles[RoleType.IO] = IOType.NULL.value

        # sort labels according to enum sorting
        role_types = list(RoleType)
        roles = sorted(self.roles.items(), key=lambda x: role_types.index(x[0]))

        # build label shapes
        pos = V(self.pos)
        for role_type, functions in roles:
            if role_type not in core.roles:
                continue
            role: Role = core.roles[role_type]
            texts = role.format(functions, hidden=hidden)
            for text in texts:
                params = dict(
                    pos=V(pos),
                    label_dir=pad.label_dir,
                    label_size=pad.label_size,
                    role_type=role_type,
                    ratio=role.ratio,
                    color=role.color,
                )
                match role_type:
                    case RoleType.IO:
                        shape = IOLine(
                            **params,
                            type=IOType(text),
                            **io_extra,
                        )
                    case _:
                        shape = Block(
                            **params,
                            text=text,
                            **block_extra,
                        )
                pos.x += (shape.width + shape.padding.x * 2) * shape.dirv
                self.labels.append(shape)

    def move(self, vec: V):
        self.pos += vec
        for shape in self.labels:
            shape.move(vec)

    def draw(self, dwg: Drawing):
        for shape in self.labels:
            shape.draw(dwg)

    @property
    def x1(self) -> float:
        return min(self.labels, key=lambda t: t.x1).x1

    @property
    def y1(self) -> float:
        return min(self.labels, key=lambda t: t.y1).y1

    @property
    def x2(self) -> float:
        return max(self.labels, key=lambda t: t.x2).x2

    @property
    def y2(self) -> float:
        return max(self.labels, key=lambda t: t.y2).y2
