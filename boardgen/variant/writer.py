# Copyright (c) Kuba Szczodrzyński 2022-06-15.

import os
import re
from os.path import dirname

from ..core import Core
from ..models.board import Board
from ..models.enums import RoleType
from ..models.pcb import PinDict
from .features import PinFeatures
from .parts import VariantParts
from .section import SectionType

# map of RoleTypes to variant.h SectionTypes
SECTION_MAP = {
    RoleType.SPI: SectionType.SPI,
    RoleType.I2C: SectionType.WIRE,
    RoleType.UART: SectionType.SERIAL,
}

# map of RoleTypes to PinFeatures
FEATURE_MAP = {
    RoleType.ARD_D: PinFeatures.PIN_GPIO,
    RoleType.ARD_A: PinFeatures.PIN_ADC,
    RoleType.PWM: PinFeatures.PIN_PWM,
    RoleType.I2C: PinFeatures.PIN_I2C,
    RoleType.I2S: PinFeatures.PIN_I2S,
    RoleType.IRQ: PinFeatures.PIN_IRQ,
    RoleType.JTAG: PinFeatures.PIN_JTAG,
    RoleType.SPI: PinFeatures.PIN_SPI,
    RoleType.SWD: PinFeatures.PIN_SWD,
    RoleType.UART: PinFeatures.PIN_UART,
}

# (indexed) communication ports with lists of required signals
PORT_SIGNALS = {
    RoleType.SPI: ["SCK", "MISO", "MOSI"],
    RoleType.I2C: ["SDA", "SCL"],
    RoleType.UART: ["TX"],
}

# list of RoleTypes to include in SectionType.MACROS
MACROS_ROLES = list(PORT_SIGNALS.keys()) + [
    RoleType.GPIO,
    RoleType.ADC,
    RoleType.PWM,
]

# RoleTypes not included in the variant.cpp comment lines
ROLES_HIDDEN = ["ARD_A", "ARD_D", "IO", "C_NAME"]


class VariantWriter(VariantParts):
    core: Core

    def __init__(self, core: Core) -> None:
        self.core = core
        self.pins = {}
        self.sections = {}
        self.gpio_map = {}
        self.static_pins = {}

    @staticmethod
    def read_pin(pin: PinDict) -> tuple[str, str, int] | None:
        name = pin.get(RoleType.GPIO, None) or pin.get(RoleType.ADC, None)
        c_name = pin.get(RoleType.C_NAME, name)
        if not name:
            return None
        number = pin.get(RoleType.GPIONUM, None)
        if number is not None:
            return name, c_name, int(number)
        number = re.sub(r"\D", "", name)
        return name, c_name, int(number)

    def generate(self, board: Board):
        pcb = board.pcb
        if not pcb or not pcb.pinout:
            return
        if not board.has_arduino_core:
            return

        self.add_item(SectionType.PINS, "PINS_COUNT", 0, "Total GPIO count")
        self.add_item(SectionType.PINS, "NUM_DIGITAL_PINS", 0, "Digital inputs/outputs")
        self.add_item(SectionType.PINS, "NUM_ANALOG_INPUTS", 0, "ADC inputs")
        self.add_item(SectionType.PINS, "NUM_ANALOG_OUTPUTS", 0, "PWM & DAC outputs")

        # { role_type: { index: { signal: [...pin_numbers] } } }
        ports: dict[RoleType, dict[int, dict[str, list[int]]]] = {}
        for role_type in PORT_SIGNALS.keys():
            ports[role_type] = {}
        max_pin_number = 0

        for pin in pcb.pinout.values():
            pin_tuple = self.read_pin(pin)
            if not pin_tuple:
                continue
            pin_name, c_name, pin_number = pin_tuple

            arduino_name = None
            ard_d = pin.get(RoleType.ARD_D, None)
            ard_a = pin.get(RoleType.ARD_A, None)
            if ard_d:
                self.add_item(SectionType.ARDUINO, f"PIN_{ard_d}", pin_number, c_name)
                self.static_pins[ard_d] = f"PIN_{ard_d}"
                arduino_name = ard_d
            if ard_a:
                self.add_item(SectionType.ARDUINO, f"PIN_{ard_a}", pin_number, c_name)
                self.static_pins[ard_a] = f"PIN_{ard_a}"
                arduino_name = arduino_name or ard_a

            if not arduino_name:
                continue
            self.gpio_map[pin_number] = arduino_name
            max_pin_number = max(max_pin_number, pin_number)

            pin_comment = []
            for role_type, values in pin.items():
                if role_type.name in ROLES_HIDDEN:
                    continue
                role = self.core.role(role_type)
                if not role:
                    continue
                pin_comment += role.format(values, long=True, hidden=ROLES_HIDDEN)
                if role_type not in MACROS_ROLES:
                    continue
                roles_short = role.format(values, long=False, hidden=ROLES_HIDDEN)
                for text in roles_short:
                    self.add_item(SectionType.MACROS, f"PIN_{text}", pin_number, c_name)
            pin_comment = ", ".join(pin_comment)

            # add the pin to the list
            new_added = self.add_pin(arduino_name, c_name, pin_comment)
            # calculate new counters
            if new_added:
                self.increment_item(SectionType.PINS, "PINS_COUNT")
                if RoleType.ARD_D in pin:
                    self.increment_item(SectionType.PINS, "NUM_DIGITAL_PINS")
                if RoleType.ARD_A in pin:
                    self.increment_item(SectionType.PINS, "NUM_ANALOG_INPUTS")
                if RoleType.PWM in pin:
                    self.increment_item(SectionType.PINS, "NUM_ANALOG_OUTPUTS")

            # add roles for the pin
            for role_type in pin.keys():
                if role_type not in FEATURE_MAP:
                    continue
                self.add_pin_feature(arduino_name, FEATURE_MAP[role_type])

            # find all indexed interfaces this pin belongs to
            for role_type, roles in pin.items():
                if role_type not in ports:
                    continue
                if not isinstance(roles, list):
                    roles = [str(roles)]
                for role in roles:
                    # require "1_RX" format
                    if not role[0].isnumeric() or role[1] != "_":
                        continue
                    (index, _, port) = role.partition("_")
                    index = int(index)
                    if index not in ports[role_type]:
                        ports[role_type][index] = {}
                    if port not in ports[role_type][index]:
                        ports[role_type][index][port] = []
                    ports[role_type][index][port].append(pin_number)

        # { role_type: { index: { signal: [...pin_numbers] } } }
        for role_type, interfaces in ports.items():
            section = SECTION_MAP[role_type]
            for index, signals in interfaces.items():
                if not all(s in signals for s in PORT_SIGNALS[role_type]):
                    # skip incomplete ports (i.e. only SDA1 available)
                    continue
                self.increment_item(
                    SectionType.PORTS,
                    f"{section.name}_INTERFACES_COUNT",
                )
                for signal, pin_numbers in signals.items():
                    self.add_item(SectionType.PORTS, f"HAS_{section.name}{index}", 1)
                    key = f"PIN_{section.name}{index}_{signal}"
                    if len(pin_numbers) > 1:
                        for i, pin in enumerate(pin_numbers):
                            c_name = self.pins[self.gpio_map[pin]][0]
                            self.add_item(section, f"{key}_{i}", pin, c_name)
                    else:
                        c_name = self.pins[self.gpio_map[pin_numbers[0]]][0]
                        self.add_item(section, key, pin_numbers[0], c_name)

        self.add_item(
            SectionType.PINS,
            "PINS_GPIO_MAX",
            max_pin_number,
            "Last usable GPIO number",
        )

    def save_h(self, output: str, board_name: str):
        os.makedirs(dirname(output), exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            lines = [
                f"/* This file was auto-generated from {board_name} using boardgen */",
                "",
                "#pragma once",
                "",
                self.format_sections(),
            ]
            f.write("\n".join(lines))

    def save_c(self, output: str, board_name: str):
        os.makedirs(dirname(output), exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            lines = [
                f"/* This file was auto-generated from {board_name} using boardgen */",
                "",
                "#include <Arduino.h>",
                "",
                "#ifdef LT_VARIANT_INCLUDE",
                "#include LT_VARIANT_INCLUDE",
                "#endif",
                "",
                self.format_pins(),
                "",
            ]
            f.write("\n".join(lines))
