# Copyright (c) Kuba Szczodrzyński 2022-05-11.

from ..utils import Model, sizeof
from .flash_region import FlashRegion
from .pcb import Pcb


class Board(Model):
    build: "BoardBuild"
    connectivity: list[str]
    debug: "BoardDebug"
    doc: "BoardDoc"
    flash: list[FlashRegion]
    frameworks: list[str]
    name: str
    pcb: Pcb
    upload: "BoardUpload"
    url: str
    vendor: str

    @property
    def size_flash(self) -> str:
        return sizeof(self.upload.flash_size)

    @property
    def size_firmware(self) -> str:
        return sizeof(self.upload.maximum_size)

    @property
    def size_ram(self) -> str:
        return sizeof(self.upload.maximum_ram_size)

    @property
    def cpu_freq(self) -> str:
        f_cpu = "".join(c for c in self.build.f_cpu if c.isnumeric())
        return sizeof(int(f_cpu), suffix="Hz", base=1000)


class BoardBuild(Model):
    f_cpu: str
    family: str
    mcu: str
    variant: str


class BoardDebug(Model):
    protocol: str
    protocols: list[str]


class BoardDoc(Model):
    params: "BoardDocParams"


class BoardDocParams(Model):
    extra: dict[str, str]
    manufacturer: str
    series: str
    voltage: str


class BoardUpload(Model):
    flash_size: int
    maximum_ram_size: int
    maximum_size: int
    protocol: str
    protocols: list[str]
    speed: int


Board.update_forward_refs()
BoardDoc.update_forward_refs()