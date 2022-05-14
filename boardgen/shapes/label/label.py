# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from svgwrite import Drawing

from ...models.enums import IOType, RoleType, RoleValue
from ...models.role import Role
from ...shapes.base import Shape
from ...vector import V
from ..base import LabelShape
from .block import Block
from .io_line import IOLine

roles_idxswap = [
    RoleType.UART,
    RoleType.SPI,
    RoleType.I2C,
    RoleType.I2S,
    RoleType.TMR,
]
roles_nameidx = [
    RoleType.ADC,
    RoleType.PWM,
    RoleType.WAKE,
]
roles_arduino = [
    RoleType.ARD,
    RoleType.ARD_D,
    RoleType.ARD_A,
]


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

        labels: list[tuple[RoleType, str]] = [
            (RoleType.PHYSICAL, str(pin)),
        ]

        for role_type, values in self.roles.items():
            # force a list
            if not isinstance(values, list):
                values = [str(values)]

            for text in values:
                # skip hidden texts
                if role_type in roles_idxswap and text[0].isnumeric():
                    if text[2:] in hidden:
                        continue
                    text = text[2:] + text[0]
                # append role name to number
                elif role_type in roles_nameidx and text.isnumeric():
                    text = role_type.name + text
                # SWDIO / SWCLK
                elif role_type == RoleType.SWD:
                    text = "SW" + text
                # convert voltage
                elif role_type == RoleType.PWR and text.replace(".", "").isnumeric():
                    text = float(text)
                    if text == 0.0:
                        role_type = RoleType.GND
                        text = "GND"
                    elif int(text) == text:
                        text = f"{int(text)}V"
                    else:
                        text = str(text).replace(".", "V")
                # change Arduino A0/D0 to roles
                elif role_type in roles_arduino:
                    role_type = RoleType.ARD_D if text[0] == "D" else RoleType.ARD_A
                # remove hidden roles
                if role_type.name in hidden or text in hidden:
                    continue
                labels.append((role_type, text))

        # sort labels according to enum sorting
        role_types = list(RoleType)
        labels = sorted(labels, key=lambda x: role_types.index(x[0]))

        # build label shapes
        pos = V(self.pos)
        for role_type, text in labels:
            if role_type not in core.roles:
                continue
            role: Role = core.roles[role_type]
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
