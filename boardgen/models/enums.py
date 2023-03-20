# Copyright (c) Kuba Szczodrzyński 2022-05-11.

from enum import Enum


class ShapeType(Enum):
    RECT = "rect"
    CIRCLE = "circle"
    TEXT = "text"
    SUBSHAPE = "include"


class Side(Enum):
    FRONT = "front"
    BACK = "back"


class LabelDir(Enum):
    LEFT = "left"
    RIGHT = "right"


class RoleType(Enum):
    NC = "NC"
    C_NAME = "C_NAME"
    IO = "IO"
    IRQ = "IRQ"
    PHYSICAL = "PHYSICAL"
    PWR = "PWR"
    GND = "GND"
    CTRL = "CTRL"
    IC = "IC"
    GPIO = "GPIO"
    GPIONUM = "GPIONUM"
    ADC = "ADC"

    ARD_D = "ARD_D"
    ARD_A = "ARD_A"

    UART = "UART"
    I2C = "I2C"
    I2S = "I2S"
    DVP = "DVP"
    SPI = "SPI"
    SD = "SD"
    USB = "USB"
    IRDA = "IRDA"

    PWM = "PWM"
    TMR = "TMR"
    WAKE = "WAKE"
    RTC = "RTC"

    JTAG = "JTAG"
    SWD = "SWD"
    FLASH = "FLASH"


class IOType(Enum):
    NC = "NC"
    IO = "IO"
    I = "I"
    O = "O"
    PWM = "PWM"
    PWR = "PWR"
    NULL = "NULL"


RoleValue = list[str] | str | int | float | IOType | None
