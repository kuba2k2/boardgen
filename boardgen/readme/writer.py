# Copyright (c) Kuba Szczodrzyński 2022-05-14.

import os
from os.path import dirname

from natsort import natsorted

from ..core import Core
from ..models import Board
from ..models.board import BoardDoc, BoardDocParams
from ..models.enums import RoleType
from ..models.flash_region import FlashRegion
from .parts import ReadmeParts


class ReadmeWriter(ReadmeParts):
    core: Core
    items: list[str] = []

    def __init__(self, core: Core) -> None:
        self.core = core
        self.items = []

    def clear(self):
        self.items = []

    def write(self, board: Board):
        if not board.doc:
            board.doc = BoardDoc()
        if not board.doc.params:
            board.doc.params = BoardDocParams()

        # Info
        self.add_heading(board.name)
        self.add_styled("*", "by", board.vendor)
        if board.url:
            self.add_link("Product page", board.url)
        if board.doc.links:
            self.add_list(
                *[[self.get_link(text, href)] for text, href in board.doc.links.items()]
            )

        # Specifications
        header = ["Parameter", "Value"]
        mcu = board.build.mcu.upper()
        if board.doc.mcu and board.doc.mcu.upper() != mcu:
            mcu += f" ({board.doc.mcu.upper()})"
        rows = [
            ["Board code", f"`{board.id}`"],
            ["MCU", mcu],
        ]
        if board.doc.params.manufacturer:
            rows.append(["Manufacturer", board.doc.params.manufacturer])
        if board.doc.params.series:
            rows.append(["Series", board.doc.params.series])
        rows.append(["Frequency", board.cpu_freq])
        rows.append(["Flash size", board.size_flash])
        rows.append(["RAM size", board.size_ram])
        if board.doc.params.voltage:
            rows.append(["Voltage", board.doc.params.voltage])
        if board.pcb and board.pcb.pinout:
            role_pins: dict[RoleType, set] = {}
            for pin in board.pcb.pinout.values():
                for role_type, roles in pin.items():
                    if role_type not in role_pins:
                        role_pins[role_type] = set()
                    if not isinstance(roles, list):
                        roles = [str(roles)]
                    for role in roles:
                        if role[0].isnumeric() and len(role) > 2 and role[1] == "_":
                            role_pins[role_type].add(role[0])
                        else:
                            role_pins[role_type].add(role)
            roles = [RoleType.GPIO, RoleType.PWM, RoleType.UART, RoleType.ADC]
            counts = [
                f"{len(role_pins[r])}x {r.name}"
                for r in roles
                if r in role_pins and len(role_pins[r])
            ]
            rows.append(["I/O", ", ".join(counts)])
        if board.doc.params.extra:
            rows.extend([[k, v] for k, v in board.doc.params.extra.items()])
        if board.doc.fccid:
            link = self.get_link(board.doc.fccid, f"https://fccid.io/{board.doc.fccid}")
            rows.append(["FCC ID", link])
        self.add_table(header, *rows)

        # Usage
        self.add_heading("Usage", 2)
        self.add_text("**Board code:**", f"`{board.id}`")
        if self.core.is_libretiny:
            family_component_map = {
                "realtek-amb": "rtl87xx",
                "beken-72xx": "bk72xx",
            }

            self.add_text("In `platformio.ini`:")
            code = [
                f"[env:{board.id}]",
                "platform = libretiny",
                f"board = {board.id}",
                "framework = arduino",
            ]
            self.add_code(code, lang="ini")

            component = None
            # noinspection PyBroadException
            try:
                from ltchiptool import Family

                family = Family.get(board.build.family)
                for f in family.inheritance:
                    if f.name in family_component_map:
                        component = family_component_map[f.name]
                        break
            except Exception:
                pass

            if component:
                self.add_text("In ESPHome YAML:")
                code = [
                    f"{component}:",
                    "  board: " + board.id,
                ]
                self.add_code(code, lang="yaml")

        # Pinout
        if board.pcb and board.pcb.pinout:
            if board.pcb.templates:
                self.add_heading("Pinout", 2)
                self.add_img("Pinout", f"{board.id}.svg")

            self.add_heading("Pin functions", 2)
            header = ["Name(s)", "UART", "I²C", "SPI", "PWM", "Other"]
            rows = []
            gpio_pins: dict[str, dict[RoleType, list[str]]] = {}
            roles = self.core.roles
            hidden = board.pcb.pinout_hidden.split(",")

            for pin in board.pcb.pinout.values():
                if RoleType.GPIO not in pin:
                    continue
                gpio = pin[RoleType.GPIO]
                gpio_pins[gpio] = {}
                for role_type, functions in pin.items():
                    if role_type not in roles:
                        continue
                    role_text = roles[role_type].format(
                        functions,
                        long=False,
                        hidden=hidden,
                    )
                    gpio_pins[gpio][role_type] = role_text

            for num in natsorted(gpio_pins.keys()):
                pin = gpio_pins[num]
                rows.append(
                    [
                        pin.get(RoleType.GPIO, []) + pin.get(RoleType.ADC, []),
                        pin.get(RoleType.UART, []),
                        pin.get(RoleType.I2C, []),
                        pin.get(RoleType.SPI, []),
                        pin.get(RoleType.PWM, []),
                        pin.get(RoleType.SWD, [])
                        + pin.get(RoleType.JTAG, [])
                        + pin.get(RoleType.DVP, []),
                    ]
                )
            for i, row in enumerate(rows):
                rows[i] = [
                    ", ".join(col) if isinstance(col, list) else col for col in row
                ]
            self.add_table(header, *rows)

        # Flash
        if board.flash:
            self.add_heading("Flash memory map", 2)
            self.add_text(
                "Flash size:",
                board.size_flash,
                "/",
                f"{format(board.upload.flash_size, ',d')} B",
                "/",
                "0x%X" % board.upload.flash_size,
            )
            self.add_text("Hex values are in bytes.")
            names = self.core.flash
            flash = sorted(board.flash, key=lambda reg: reg.start)
            header = ["Name", "Start", "Length", "End"]
            rows = []
            prev_end = 0
            for reg in flash:
                reg.hex_size_len = 0
                name = names[reg.name] if reg.name in names else reg.name
                if prev_end < reg.start:
                    res = FlashRegion(
                        name="res",
                        offset=prev_end,
                        length=reg.start - prev_end,
                    )
                    res.hex_offs_len = reg.hex_offs_len
                    rows.append(["(reserved)"] + res.lst)
                rows.append([name] + reg.lst)
                prev_end = reg.end
            self.add_table(header, *rows)

        # Extras
        if board.doc.extra:
            self.items += board.doc.extra

    def to_string(self) -> str:
        return "\n\n".join(self.items)

    def save(self, output: str):
        os.makedirs(dirname(output), exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(self.to_string())
            f.write("\n")
