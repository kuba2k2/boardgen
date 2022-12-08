# Copyright (c) Kuba Szczodrzyński 2022-05-11.

from pydantic.color import Color

from ..utils import Model
from .enums import RoleType, RoleValue

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
    RoleType.SD,
    RoleType.DVP,
]
roles_arduino = [
    RoleType.ARD_D,
    RoleType.ARD_A,
]


class Role(Model):
    role_type: RoleType
    title: str
    color: Color
    ratio: float = 1.8

    def format(
        self, functions: RoleValue, long: bool = False, hidden: list[str] = []
    ) -> list[str]:
        # force a list
        if not isinstance(functions, list):
            if not functions:
                functions = [self.role_type.name]
            else:
                functions = [str(functions)]

        out = []
        for function in functions:
            # swap number and function
            if self.role_type in roles_idxswap and function[0].isnumeric():
                # skip hidden texts
                if function[2:] in hidden:
                    continue
                if long:
                    function = self.role_type.name + function
                else:
                    function = function[2:] + function[0]
            # append role name to number
            elif self.role_type in roles_nameidx and function.isnumeric():
                function = self.role_type.name + function
            elif self.role_type in roles_nameidx and long:
                function = self.role_type.name + "_" + function
            # SWDIO / SWCLK
            elif self.role_type == RoleType.SWD:
                function = "SW" + function
            # convert voltage
            elif (
                self.role_type == RoleType.PWR and function.replace(".", "").isnumeric()
            ):
                function = float(function)
                # decimal voltage
                if int(function) == function:
                    function = f"{int(function)}V"
                # floating point voltage
                else:
                    function = str(function).replace(".", "V")
            # remove hidden roles
            if self.role_type.name in hidden or function in hidden:
                continue
            out.append(function)
        return out
