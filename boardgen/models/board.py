# Copyright (c) Kuba Szczodrzyński 2022-05-11.

from ..utils import Model, sizeof
from .flash_region import FlashRegion
from .pcb import Pcb


class Board(Model):
    build: "BoardBuild"
    connectivity: list[str] = None
    debug: "BoardDebug" = None
    doc: "BoardDoc" = None
    flash: list[FlashRegion] = None
    name: str
    pcb: Pcb = None
    upload: "BoardUpload"
    url: str = None
    vendor: str

    @property
    def id(self) -> str:
        return self.build.variant

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

    @property
    def has_arduino_core(self) -> bool:
        return True


class BoardBuild(Model):
    f_cpu: str
    family: str
    mcu: str
    variant: str


class BoardDebug(Model):
    protocol: str
    protocols: list[str]


class BoardDoc(Model):
    params: "BoardDocParams" = None
    links: dict[str, str] = None
    extra: list[str] = None
    fccid: str = None


class BoardDocParams(Model):
    extra: dict[str, str] = None
    manufacturer: str = None
    series: str = None
    voltage: str = None


class BoardUpload(Model):
    flash_size: int
    maximum_ram_size: int
    maximum_size: int
    protocol: str = None
    protocols: list[str] = None
    speed: int = None


Board.update_forward_refs()
BoardDoc.update_forward_refs()
