# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from ..utils import Model, sizeof


class FlashRegion(Model):
    name: str
    offset: int
    length: int

    title: str = None
    read_only: bool = False
    hex_offs_len: str = 6
    hex_size_len: str = 0

    @property
    def start(self) -> int:
        return self.offset

    @property
    def end(self) -> int:
        return self.offset + self.length

    @property
    def start_hex(self) -> str:
        if not self.hex_offs_len:
            return "0x%X" % self.start
        return f"0x%0{self.hex_offs_len}X" % self.start

    @property
    def end_hex(self) -> str:
        if not self.hex_offs_len:
            return "0x%X" % self.end
        return f"0x%0{self.hex_offs_len}X" % self.end

    @property
    def length_hex(self) -> str:
        if not self.hex_size_len:
            return "0x%X" % self.length
        return f"0x%0{self.hex_size_len}X" % self.length

    @property
    def length_str(self) -> str:
        return sizeof(self.length)

    @property
    def lst(self) -> list[str]:
        return [self.start_hex, self.length_str + " / " + self.length_hex, self.end_hex]
