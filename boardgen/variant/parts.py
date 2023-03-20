# Copyright (c) Kuba Szczodrzyński 2022-06-15.

from abc import ABC

from natsort import natsort_keygen

from ..models import Role
from .features import PinFeatures
from .section import SectionType

SectionItem = tuple[int, str | None]


class VariantParts(ABC):
    # { name: (c_name, features, comment, roles) }
    pins: dict[str, tuple[str, PinFeatures, str]]
    # { pin_number: arduino_name }
    gpio_map: dict[int, str]
    # { section_type: { key: (value, comment) } }
    sections: dict[SectionType, dict[str, SectionItem]]
    # { name: pin_name }
    static_pins: dict[str, str]

    def add_pin(self, name: str, gpio: str, comment: str = None) -> bool:
        if name in self.pins:
            return False
        self.pins[name] = (gpio, PinFeatures.PIN_NONE, comment)
        return True

    def add_pin_feature(self, name: str, feature: PinFeatures):
        if name not in self.pins:
            return
        (gpio, features, comment) = self.pins[name]
        features &= ~PinFeatures.PIN_NONE
        features |= feature
        self.pins[name] = (gpio, features, comment)

    def add_item(
        self,
        section: SectionType,
        key: str,
        value: int,
        comment: str = None,
    ):
        if section not in self.sections:
            self.sections[section] = {}
        self.sections[section][key] = (value, comment)

    def increment_item(self, section: SectionType, key: str):
        if section not in self.sections:
            self.sections[section] = {}
        if key in self.sections[section]:
            value, comment = self.sections[section][key]
            self.sections[section][key] = (value + 1, comment)
        else:
            self.sections[section][key] = (1, None)

    def format_pins(self) -> str:
        name_list = "lt_arduino_pin_info_list"
        name_map = "lt_arduino_pin_gpio_map"
        out = [
            "// clang-format off",
            f"PinInfo {name_list}[PINS_COUNT] = {{",
        ]

        def sort_pins(item):
            # (name, (c_name, features, comment))
            return int(item[0][1:]) + (1000 if item[0][0] == "D" else 2000)

        pins: list[tuple[str, tuple[str, PinFeatures, str]]]
        # noinspection PyTypeChecker
        pins = sorted(self.pins.items(), key=sort_pins)
        gpio_map = sorted(self.gpio_map.items())

        pin_name_map: dict[str, tuple[str, int]] = {}
        for index, (arduino_name, (c_name, _, _)) in enumerate(pins):
            pin_name_map[arduino_name] = c_name, index

        len_c_name = 0
        len_features = 0
        for _, (c_name, features, _) in pins:
            features = str(features).partition(".")[2].replace("|", " | ")
            len_c_name = max(len_c_name, len(c_name))
            len_features = max(len_features, len(features))

        # (name, (c_name, features, comment))
        for name, (c_name, features, comment) in pins:
            features = str(features).partition(".")[2]
            features = " | ".join(reversed(features.split("|")))
            out.append(f"\t// {name}: {comment}")
            pad_c_name = " " * (len_c_name - len(c_name))
            pad_features = " " * (len_features - len(features))
            out.append(
                f"\t{{{c_name}, {pad_c_name}{features}, {pad_features}PIN_NONE, 0}},"
            )
        out.append("};\n")
        out.append(f"PinInfo *{name_map}[] = {{")

        max_pin = max(pin for pin, _ in gpio_map)
        max_idx = max(idx for _, (_, idx) in pin_name_map.items())
        len_pin = len(str(max_pin))
        len_idx = len(str(max_idx))

        for pin_number, arduino_name in gpio_map:
            c_name, index = pin_name_map[arduino_name]
            pad_pin = " " * (len_pin - len(str(pin_number)))
            pad_idx = " " * (len_idx - len(str(index)))
            out.append(
                f"\t[{pin_number}]{pad_pin} = "
                f"&({name_list}[{index}]), {pad_idx}"
                f"// {c_name} ({arduino_name})",
            )

        out.append("};")
        out.append("// clang-format on")
        return "\n".join(out)

    def format_sections(self) -> str:
        out = [
            "// clang-format off",
            "",
        ]

        def sort_pins(item):
            # (key, (value, comment))
            pin = item[0]
            shift = 10000
            if pin.startswith("PIN_"):
                pin = pin[4:]
                shift = 0
            return int(pin[1:]) + (1000 if pin[0] == "D" else 2000) + shift

        natsort_key = natsort_keygen()

        for section_type in SectionType:
            if section_type not in self.sections:
                continue
            section = self.sections[section_type].items()
            out.append(f"// {section_type.value}")
            out.append(f"// {len(section_type.value) * '-'}")
            max_key = 0
            max_value = 0

            for key, (value, _) in section:
                value = str(value)
                if key.startswith("PIN_"):
                    value = f"{value}u"
                max_key = max(max_key, len(key))
                max_value = max(max_value, len(value))

            if section_type == SectionType.ARDUINO:
                section = sorted(section, key=sort_pins)
            elif section_type != SectionType.PINS:
                section = sorted(section, key=natsort_key)

            for key, (value, comment) in section:
                value = str(value)
                if key.startswith("PIN_"):
                    value = f"{value}u"
                if comment:
                    comment = f"// {comment}"
                else:
                    comment = ""
                pad_key = " " * (max_key - len(key))
                pad_value = " " * (max_value - len(value))
                out.append(
                    f"#define {key}{pad_key} {value}{pad_value} {comment}".strip()
                )
            out.append("")

        heading = "Static pin names"
        out.append(f"// {heading}")
        out.append(f"// {len(heading) * '-'}")
        for name, pin_name in sorted(self.static_pins.items(), key=natsort_key):
            out.append(f"static const unsigned char {name} = {pin_name};")
        out.append("")

        return "\n".join(out)
