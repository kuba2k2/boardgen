# Copyright (c) Kuba Szczodrzyński 2022-06-15.

from abc import ABC

from .features import PinFeatures
from .section import SectionType

SectionItem = tuple[str, object, str]


class VariantParts(ABC):
    pins: dict[str, tuple[str, PinFeatures, str]] = {}
    sections: dict[SectionType, list[SectionItem]] = {}
    sorted_pins: list[tuple[str, str, PinFeatures, str]] = []
    sorted_sections: list[tuple[SectionType, list[SectionItem]]] = []

    def add_pin(self, name: str, gpio: str, comment: str = None) -> bool:
        if name in self.pins:
            return False
        self.pins[name] = (gpio, PinFeatures.PIN_NONE, comment)
        return True

    def add_pin_feature(self, name: str, feature: PinFeatures):
        if name not in self.pins:
            return
        (gpio, features, comment) = self.pins[name]
        features &= ~(PinFeatures.PIN_NONE)
        features |= feature
        self.pins[name] = (gpio, features, comment)

    def add_item(
        self, section: SectionType, key: str, value: object, comment: str = None
    ):
        if section not in self.sections:
            self.sections[section] = []
        self.sections[section].append((key, value, comment))

    def increment_item(self, section: SectionType, key: str):
        if section not in self.sections:
            self.sections[section] = []
        for i, (ikey, value, comment) in enumerate(self.sections[section]):
            if ikey != key:
                continue
            self.sections[section][i] = (key, value + 1, comment)
            return
        self.sections[section].append((key, 1, None))

    def format_pins(self) -> str:
        out = [
            "// clang-format off",
            "PinInfo pinTable[PINS_COUNT] = {",
        ]
        items: list[tuple[str, str, str, str]] = []
        max_gpio = 0
        max_features = 0
        for name, gpio, features, comment in self.sorted_pins:
            features_str = []
            for feature in PinFeatures:
                if features & feature:
                    features_str.append(feature.name)
            features_str = " | ".join(features_str)
            items.append((name, gpio, features_str, comment))
            max_gpio = max(max_gpio, len(gpio))
            max_features = max(max_features, len(features_str))
        for name, gpio, features, comment in items:
            out.append(f"\t// {name}: {comment}")
            pad_gpio = " " * (max_gpio - len(gpio))
            pad_features = " " * (max_features - len(features))
            out.append(
                f"\t{{{gpio}, {pad_gpio}{features}, {pad_features}PIN_NONE, 0}},"
            )
        out.append("};")
        out.append("// clang-format on")
        return "\n".join(out)

    def format_sections(self) -> str:
        out = [
            "// clang-format off",
            "",
        ]
        for section_type, items in self.sorted_sections:
            out.append(f"// {section_type.value}")
            out.append(f"// {len(section_type.value) * '-'}")
            max_key = 0
            max_value = 0
            for key, value, _ in items:
                value = str(value)
                max_key = max(max_key, len(key))
                max_value = max(max_value, len(value))
            for key, value, comment in items:
                value = str(value)
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
        return "\n".join(out)
