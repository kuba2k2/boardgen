# Copyright (c) Kuba Szczodrzyński 2022-06-15.

from enum import Enum


class SectionType(Enum):
    PINS = "Pins"
    LEDS = "LEDs"
    ANALOG = "Analog pins"
    SPI = "SPI Interfaces"
    WIRE = "Wire Interfaces"
    SERIAL = "Serial ports"
    MACROS = "Pin function macros"
