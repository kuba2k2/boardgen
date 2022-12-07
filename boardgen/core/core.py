# Copyright (c) Kuba Szczodrzyński 2022-05-11.

import json
import re
from importlib.metadata import version
from os.path import dirname, isfile, join

from ..mixins import HasId, ParentType
from ..models import Board, FlashRegion, Pcb, Role, RoleType, ShapeType, Side, Template
from ..models.enums import RoleValue
from ..shapes.base import Shape
from ..shapes.circle import Circle
from ..shapes.group import ShapeGroup
from ..shapes.label import Label
from ..shapes.rect import Rect
from ..shapes.text import Text
from ..utils import load_json, var
from ..vector import V
from .cache import CoreCache
from .getters import CoreGetters


class Core(CoreCache, CoreGetters):
    shape_ctors: dict[ShapeType, type]
    is_libretuya: bool = False

    _dir_base: str
    _dirs_boards: list[str]
    _dirs_shapes: list[str]
    _dirs_templates: list[str]
    _file_presets: str
    _file_roles: str
    _presets: dict[str, dict] = None
    _roles: dict[RoleType, Role] = None
    _flash: dict[str, str] = None

    def __init__(self) -> None:
        self._dir_base = join(dirname(__file__), "..", "res")
        self._dirs_boards = [
            join(dirname(__file__), "..", "..", "..", "..", "boards"),
            join(self._dir_base, "boards"),
            "boards",
        ]
        self._dirs_shapes = [
            join(self._dir_base, "shapes"),
        ]
        self._dirs_templates = [
            join(self._dir_base, "templates"),
        ]
        self._file_presets = join(self._dir_base, "presets.json")
        self._file_roles = join(self._dir_base, "roles.json")
        self._file_flash = join(self._dir_base, "flash.json")
        self.shape_ctors = {
            ShapeType.RECT: Rect,
            ShapeType.CIRCLE: Circle,
            ShapeType.SUBSHAPE: ShapeGroup,
            ShapeType.TEXT: Text,
        }
        self.is_libretuya = isfile(
            join(dirname(__file__), "..", "..", "..", "..", "platform.json")
        ) or isfile("families.json")

    @property
    def version(self) -> str | None:
        pyproject = join(dirname(__file__), "..", "..", "pyproject.toml")
        if isfile(pyproject):
            with open(pyproject, "r", encoding="utf-8") as f:
                text = f.read()
                ver = re.search(r"version\s?=\s?\"(.+?)\"", text)
                if ver:
                    return ver.group(1)
        try:
            return version("boardgen")
        except Exception:
            return None

    def add_custom_dirs(
        self,
        boards: list[str] | str = None,
        shapes: list[str] | str = None,
        templates: list[str] | str = None,
    ):
        if isinstance(boards, str):
            boards = [boards]
        if isinstance(shapes, str):
            shapes = [shapes]
        if isinstance(templates, str):
            templates = [templates]

        if boards:
            self._dirs_boards = boards + self._dirs_boards
        if shapes:
            self._dirs_shapes = shapes + self._dirs_shapes
        if templates:
            self._dirs_templates = templates + self._dirs_templates

    def add_custom_json(
        self,
        presets: dict = None,
        roles: dict = None,
        flash: dict = None,
    ):
        if presets:
            self.presets |= presets
        if roles:
            self.roles |= roles
        if flash:
            self.flash |= flash

    def build_shapes(self, name: str, parent: ParentType, pos: V = None) -> list[Shape]:
        """Load the specified shape JSON into a list of Shape objects.

        Args:
            name (str): Shape name.
            parent (ParentType): Parent object (Shape, Pcb, etc).
            pos (V | None): Move the shape by the vector. Defaults to None.
        """
        shape = self.load_shape(name)
        return [self.build_shape(parent, data, pos) for data in shape]

    def build_shape(self, parent: ParentType, data: dict, pos: V = None) -> Shape:
        """Deserialize a single shape from JSON.

        Args:
            parent (ParentType): Parent object.
            data (dict): Input JSON data.
            pos (V, optional): Move the shape by the vector. Defaults to None.
        """
        shape = Shape.deserialize(self, parent, data)
        if pos:
            shape.move(pos)
        return shape

    def build_presets(self, vars: dict) -> dict[str, dict]:
        """Return all defined presets with specified vars applied.

        Args:
            vars (dict): Variables to apply. May be None.
        """
        if not vars:
            return self.presets
        # ugly way to replace all vars
        presets = json.dumps(self.presets)
        presets = var(presets, vars)
        return json.loads(presets)

    def get_board(self, name: str) -> Board:
        """Load and build the specified board.

        Args:
            name (str): Board name.
        """
        manifest = self.load_board(name)
        pcb = manifest.get("pcb", None)
        pinout = pcb.get("pinout", None) if pcb else None
        ic_pins = pcb.get("ic", None) if pcb else None

        if pinout:
            for roles in pinout.values():
                roles: dict[str, RoleValue]
                # add IC pinout mapping from board manifest
                ic_pin = str(roles.get("IC", None))
                if ic_pins and ic_pin in ic_pins:
                    roles |= ic_pins[ic_pin]

                for role_type, functions in dict(roles).items():
                    if role_type == "ARD":
                        digital = []
                        analog = []
                        if not isinstance(functions, list):
                            functions = [str(functions)]
                        for function in functions:
                            match function[0]:
                                case "D":
                                    digital.append(function)
                                case "A":
                                    analog.append(function)
                        if digital:
                            if len(digital) != 1:
                                raise ValueError(f"Invalid digital pins: {digital}")
                            roles["ARD_D"] = digital[0]
                        if analog:
                            if len(analog) != 1:
                                raise ValueError(f"Invalid analog pins: {analog}")
                            roles["ARD_A"] = analog[0]
                        roles.pop("ARD", None)

        if "flash" in manifest and isinstance(manifest["flash"], dict):
            flash: list[FlashRegion] = []
            hex_offs_len = 0
            hex_size_len = 0
            for region, layout in manifest["flash"].items():
                (offset, _, length) = layout.partition("+")
                offset = int(offset, 16)
                length = int(length, 16)
                hex_offs_len = max(hex_offs_len, len(hex(offset)))
                hex_size_len = max(hex_size_len, len(hex(length)))
                desc = self.flash.get(region, "(unknown)")
                if not isinstance(desc, dict):
                    desc = dict(title=desc)
                flash.append(
                    FlashRegion(
                        name=region,
                        offset=offset,
                        length=length,
                        **desc,
                    )
                )
            for region in flash:
                region.hex_offs_len = hex_offs_len - 2
                region.hex_size_len = hex_size_len - 2
            manifest["flash"] = flash

        board = Board(**manifest)
        pcb = board.pcb

        if not pcb:
            return board
        pcb.vars["NAME"] = board.build.variant
        pcb.vars["TITLE"] = board.name
        pcb.vars["SYMBOL"] = pcb.symbol

        shapes = {
            Side.FRONT: [],
            Side.BACK: [],
        }
        sources: list[HasId] = []
        for template_name in pcb.templates:
            template = Template(**self.load_template(template_name))
            template.vars |= pcb.vars
            pcb.pads |= template.pads
            pcb.test_pads |= template.test_pads
            sources.append(template)
        sources.append(pcb)

        for side in Side:
            for parent in sources:
                parent.id_suffix = side.value
                shapes[side] += [
                    self.build_shape(parent, data)
                    for data in getattr(parent, side.value)
                ]
                parent.id_suffix = None

        for side, items in shapes.items():
            pcb.shapes[side] = ShapeGroup.wrap(self, name + "." + side.value, items)

        return board

    def build_labels(self, pcb: Pcb, side: Side) -> tuple[list[Label], V, V]:
        pads = pcb.pads
        pads |= pcb.test_pads
        pins = pcb.pinout
        hidden = pcb.pinout_hidden.split(",")

        x1, y1, x2, y2 = (None, None, None, None)
        labels: list[Label] = []
        for pin, roles in pins.items():
            if pin not in pads:
                continue
            pad = pcb.shapes[side].get_by_id(pads[pin])
            if not pad:
                continue
            label = Label(
                pos=pad.pos,
                role_type=RoleType.NC,
                ratio=1.0,
                color="#000",
                roles=roles,
            )
            label.build(self, pin, pad, hidden)
            if x1 is None:
                x1 = label.pos1.x
                y1 = label.pos1.y
                x2 = label.pos2.x
                y2 = label.pos2.y
            else:
                x1 = min(x1, label.pos1.x)
                y1 = min(y1, label.pos1.y)
                x2 = max(x2, label.pos2.x)
                y2 = max(y2, label.pos2.y)
            labels.append(label)

        return (labels, V(x1, y1), V(x2, y2))
