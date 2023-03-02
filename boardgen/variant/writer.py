# Copyright (c) Kuba Szczodrzyński 2022-06-15.

import os
import re
from os.path import dirname

from natsort import natsort_keygen

from ..core import Core
from ..models.board import Board
from ..models.enums import RoleType
from .features import PinFeatures
from .parts import VariantParts
from .section import SectionType


class VariantWriter(VariantParts):
    core: Core

    def __init__(self, core: Core) -> None:
        self.core = core
        self.pins = {}
        self.sections = {}
        self.sorted_pins = []
        self.sorted_sections = []

    def generate(self, board: Board):
        pcb = board.pcb
        if not pcb or not pcb.pinout:
            return
        if not board.has_arduino_core:
            return

        interfaces: dict[RoleType, dict[int, dict[str, list[str]]]] = {
            RoleType.SPI: {},
            RoleType.I2C: {},
            RoleType.UART: {},
        }
        interface_ports: dict[RoleType, list[str]] = {
            RoleType.SPI: ["SCK", "MISO", "MOSI"],
            RoleType.I2C: ["SDA", "SCL"],
            RoleType.UART: ["TX"],
        }
        interface_sections: dict[RoleType, SectionType] = {
            RoleType.SPI: SectionType.SPI,
            RoleType.I2C: SectionType.WIRE,
            RoleType.UART: SectionType.SERIAL,
        }
        macro_roles = [
            RoleType.GPIO,
            RoleType.ADC,
            RoleType.PWM,
        ] + list(interfaces.keys())

        analog_alias = []

        for pin in pcb.pinout.values():
            pin_digital = pin.get(RoleType.ARD_D, None)
            pin_analog = pin.get(RoleType.ARD_A, None)
            c_name = pin.get(RoleType.C_NAME, None)
            gpio = pin.get(RoleType.GPIO, None)
            adc = pin.get(RoleType.ADC, None)

            comment = []
            role_text = []
            hidden = ["ARD_A", "ARD_D", "IO", "C_NAME"]
            for role_type, roles in pin.items():
                if role_type.name in hidden:
                    continue
                role = self.core.role(role_type)
                if role:
                    comment += role.format(roles, long=True, hidden=hidden)
                    if role_type in macro_roles:
                        role_text += role.format(roles, long=False, hidden=hidden)
            comment = ", ".join(comment)

            if pin_digital:
                pin_name = pin_digital
                added = self.add_pin(pin_name, c_name or gpio, comment)
            elif pin_analog:
                pin_name = pin_analog
                added = self.add_pin(pin_name, c_name or str(adc), comment)
            else:
                continue

            # add pin role short names to generate macros
            self.add_pin_roles(pin_name, *role_text)

            if added:
                self.increment_item(SectionType.PINS, "PINS_COUNT")

            if pin_digital:
                self.add_pin_feature(pin_name, PinFeatures.PIN_GPIO)
                if added:
                    self.increment_item(SectionType.PINS, "NUM_DIGITAL_PINS")
            if pin_analog:
                self.add_pin_feature(pin_name, PinFeatures.PIN_ADC)
                if added:
                    self.increment_item(SectionType.PINS, "NUM_ANALOG_INPUTS")
                self.add_item(SectionType.ANALOG, f"PIN_{pin_analog}", pin_name)
                analog_alias.append(pin_analog)

            for role_type, roles in pin.items():
                if role_type not in interfaces:
                    continue
                if not isinstance(roles, list):
                    roles = [str(roles)]
                for role in roles:
                    # require "1_RX" format
                    if not role[0].isnumeric() or role[1] != "_":
                        continue
                    (index, _, port) = role.partition("_")
                    if index not in interfaces[role_type]:
                        interfaces[role_type][index] = {}
                    if port not in interfaces[role_type][index]:
                        interfaces[role_type][index][port] = []
                    interfaces[role_type][index][port].append(pin_name)

            if RoleType.PWM in pin:
                self.add_pin_feature(pin_name, PinFeatures.PIN_PWM)
            if RoleType.I2C in pin:
                self.add_pin_feature(pin_name, PinFeatures.PIN_I2C)
            if RoleType.I2S in pin:
                self.add_pin_feature(pin_name, PinFeatures.PIN_I2S)
            if RoleType.IRQ in pin:
                self.add_pin_feature(pin_name, PinFeatures.PIN_IRQ)
            if RoleType.JTAG in pin:
                self.add_pin_feature(pin_name, PinFeatures.PIN_JTAG)
            if RoleType.SPI in pin:
                self.add_pin_feature(pin_name, PinFeatures.PIN_SPI)
            if RoleType.SWD in pin:
                self.add_pin_feature(pin_name, PinFeatures.PIN_SWD)
            if RoleType.UART in pin:
                self.add_pin_feature(pin_name, PinFeatures.PIN_UART)

        self.add_item(SectionType.PINS, "NUM_ANALOG_OUTPUTS", 0)

        for alias in analog_alias:
            self.add_item(SectionType.ANALOG, alias, f"PIN_{alias}")

        has_interfaces = set()

        for role_type, intfs in interfaces.items():
            section = interface_sections[role_type]
            count = 0
            items = {}
            for idx in sorted(intfs.keys()):
                ports = intfs[idx]
                if not all(port in ports for port in interface_ports[role_type]):
                    # skip incomplete ports (i.e. only SDA1 available)
                    continue
                count += 1
                for port in sorted(ports.keys()):
                    pins = ports[port]
                    has_interfaces.add(f"{section.name}{idx}")
                    key = f"PIN_{section.name}{idx}_{port}"
                    if len(pins) > 1:
                        for i, pin in enumerate(pins):
                            items[f"{key}_{i}"] = pin
                    else:
                        items[key] = pins[0]
            self.add_item(section, f"{section.name}_INTERFACES_COUNT", count)
            for key, value in items.items():
                self.add_item(section, key, value)

        for name in sorted(has_interfaces):
            self.add_item(SectionType.PORTS, f"HAS_{name}", 1)

        self.prepare_data()

    def prepare_data(self):
        pins_d = []
        pins_a = []
        pins_idx = {}
        for name in sorted(self.pins.keys(), key=lambda x: int(x[1:])):
            (gpio, features, comment, roles) = self.pins[name]
            if name[0] == "D":
                pins_d.append((name, gpio, features, comment, roles))
            if name[0] == "A":
                pins_a.append((name, gpio, features, comment, roles))
        self.sorted_pins = pins_d + pins_a

        pin_macros: list[tuple[str, str]] = []
        for i, (name, gpio, _, _, roles) in enumerate(self.sorted_pins):
            pins_idx[name] = (i, gpio)
            for role in roles:
                pin_macros.append((role, name))

        # find all pins with duplicate roles (i.e. PWM0==2 and PWM0==10)
        # remove entire role types if found
        to_remove = set()
        for role, name in pin_macros:
            if sum(1 for x in pin_macros if x[0] == role) > 1:
                to_remove.add(re.sub(r"[\d]", "", role))
        for role in to_remove:
            pin_macros = [m for m in pin_macros if not m[0].startswith(role)]

        # add macros for pin functions
        for role, name in pin_macros:
            self.add_item(SectionType.MACROS, f"PIN_{role}", name)
        # sort the macros naturally
        natsort_key = natsort_keygen()
        self.sections.get(SectionType.MACROS, []).sort(key=natsort_key)

        self.sorted_sections = []
        for type in SectionType:
            if type not in self.sections:
                continue
            section = self.sections[type]
            for i, (key, value, _) in enumerate(section):
                if not key.startswith("PIN_"):
                    continue
                (idx, gpio) = pins_idx[value]
                section[i] = (key, f"{idx}u", gpio)
            self.sorted_sections.append((type, self.sections[type]))

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

    def save_cpp(self, output: str, board_name: str):
        os.makedirs(dirname(output), exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            lines = [
                f"/* This file was auto-generated from {board_name} using boardgen */",
                "",
                "#include <Arduino.h>",
                "",
                'extern "C" {',
                "",
                "#ifdef LT_VARIANT_INCLUDE",
                "#include LT_VARIANT_INCLUDE",
                "#endif",
                "",
                self.format_pins(),
                "",
                '} // extern "C"',
                "",
            ]
            f.write("\n".join(lines))
