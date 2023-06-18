#  Copyright (c) Kuba Szczodrzyński 2023-6-3.

import json
from copy import deepcopy
from enum import Enum, auto
from logging import debug, info, warning
from os import makedirs, rename, unlink
from os.path import abspath, basename, dirname, join
from shutil import copyfile

import wx
import wx.adv
import wx.xrc
from ltchiptool import Family
from ltchiptool.gui.panels.base import BasePanel
from ltchiptool.gui.utils import on_event, with_event
from ltchiptool.util.lvm import LVM

from boardgen import Core, HasVars, V
from boardgen.draw_util import draw_shapes, get_pcb_images
from boardgen.models import Board, RoleType, Template
from boardgen.shapes import Shape, ShapeGroup

from .svg import SvgPanel
from .utils import jsonpath, jsonwalk

INIT_BOARD = {
    "_base": [],
    "build": {
        "mcu": "",
        "variant": "",
    },
    "name": "",
    "url": "",
    "vendor": "",
    "doc": {
        "fccid": "",
    },
    "pcb": {
        "symbol": "",
    },
}
INIT_TEMPLATE = {
    "name": "",
    "title": "",
    "width": 10,
    "height": 10,
    "front": [],
    "back": [],
    "pads": {},
    "test_pads": {},
}
INIT_SHAPE = []
ROLE_DEFAULTS: dict[str, str | int | None] = {
    "ADC": 0,
    "ARD": "D0",
    "CTRL": "CEN",
    "C_NAME": "GPIO_00",
    "DVP": "PD0",
    "FLASH": "^FCS",
    "GND": None,
    "GPIO": "P0",
    "GPIONUM": 35,
    "I2C": "0_SDA",
    "I2S": "0_TX",
    "IC": 1,
    "IO": "I",
    "IRDA": None,
    "IRQ": None,
    "JTAG": "TMS",
    "PHYSICAL": 2,
    "PWM": 1,
    "PWR": 3.3,
    "SD": "CMD",
    "SPI": "0_SCK",
    "SWD": "DIO",
    "UART": "1_TX",
    "USB": "DN",
    "WAKE": 1,
}
SHAPE_DEFAULTS = {
    "circle": {
        "type": "circle",
        "pos": "0,0",
        "d": 1.0,
        "fill": {
            "color": "black",
        },
    },
    "rect": {
        "type": "rect",
        "pos": "0,0",
        "size": "1,1",
        "fill": {
            "color": "black",
        },
    },
    "subshape": {
        "id": "subshape_id_here",
        "name": "test_pad_1mm",
        "repeat": 1,
        "pos": "0,0",
    },
    "text": {
        "type": "text",
        "pos": "0,0",
        "text": "Text",
        "font_size": 1.0,
        "fill": {
            "color": "red",
        },
    },
}


class EditType(Enum):
    # multiple choice
    BASE = auto()
    TEMPLATE = auto()
    CONNECTIVITY = auto()
    ROLE_HIDDEN = auto()
    # single choice
    SHAPE = auto()
    SHAPE_ADD = auto()
    PRESET = auto()
    FAMILY = auto()
    ROLE = auto()
    FLASH = auto()
    # other
    COLOR = auto()


class BoardgenPanel(BasePanel):
    file_map: dict[str, str] = None
    draw_items: dict[str, str] = None
    draw_object: Board | list[Shape] | Shape
    edit_items: dict[str, tuple[str, dict]] = None
    edit_selection: str = None
    edit_path: str = ""
    edit_errors: bool = False
    edit_type: EditType | None = None
    modified: dict[str, dict] = None
    _vars: dict

    def __init__(self, parent: wx.Window, frame):
        super().__init__(parent, frame)
        self.LoadXRCFile("boardgen.xrc")

        self._shapes = []
        self._vars = {}

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Splitter = wx.SplitterWindow(self, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        self.Left: wx.Panel = self.Xrc.LoadPanel(self.Splitter, "PreviewPanel")
        self.Right: wx.Panel = self.Xrc.LoadPanel(self.Splitter, "EditPanel")
        self.Splitter.SetMinimumPaneSize(300)
        self.Splitter.SetSashGravity(0.3)
        self.Splitter.SplitVertically(self.Left, self.Right, sashPosition=-600)
        self.Sizer.Add(self.Splitter, proportion=1, flag=wx.EXPAND)
        self.SetSizer(self.Sizer)

        self.AddToNotebook("boardgen")

        self.PreviewPanel: wx.Panel = self.Left.FindWindowByName("preview_panel")
        self.PreviewBox: wx.BoxSizer = self.PreviewPanel.GetSizer()
        self.Svg = SvgPanel(self.PreviewPanel)
        self.PreviewBox.Add(self.Svg, proportion=1, flag=wx.EXPAND)

        self.EditItem = self.BindComboBox("combo_edit_item")
        self.DrawItem = self.BindComboBox("combo_preview_item")
        self.Data: wx.TextCtrl = self.FindWindowByName("input_data")
        self.Data.Bind(wx.EVT_TEXT, self.OnDataText)
        self.Data.Bind(wx.EVT_KEY_UP, self.OnDataPosition)
        self.Data.Bind(wx.EVT_LEFT_UP, self.OnDataPosition)
        self.Vars = self.BindTextCtrl("input_vars")
        self.Vars.Bind(wx.EVT_TEXT, self.OnVarsText)
        self.Path = self.BindTextCtrl("input_path")
        self.Error = self.BindTextCtrl("input_error")
        self.Save = self.BindButton("button_save", self.OnSaveClick)
        self.Edit = self.BindButton("button_edit", self.OnEditClick)
        self.Format = self.BindButton("button_format", self.OnFormatClick)
        self.Choose = self.BindButton("button_choose", self.OnChooseClick)
        self.Revert = self.BindButton("button_revert", self.OnRevertClick)
        self.Discard = self.BindButton("button_discard", self.OnDiscardClick)
        self.Modified: wx.adv.HyperlinkCtrl = self.BindWindow(
            "label_modified",
            (wx.adv.EVT_HYPERLINK, self.OnModifiedClick),
        )

        self.lvm = LVM.get()
        self.core = Core()
        self.core.add_custom_dirs(
            boards=join(self.lvm.path(), "boards"),
            shapes=join(self.lvm.path(), "boards", "shapes"),
            templates=join(self.lvm.path(), "boards", "templates"),
        )
        self.core.json_hook = self.AddEditItem

        self.file_map = {}
        self.draw_items = {}
        self.edit_items = {}
        self.modified = {}

        self.ReloadLists()

    def GetSettings(self) -> dict:
        return dict(
            draw_item=self.draw_item,
            edit_item=self.edit_item and self.edit_item[0],
            split=self.Splitter.GetSashPosition(),
            user_vars=self.user_vars,
        )

    def SetSettings(
        self,
        draw_item: str = None,
        edit_item: str = None,
        split: int = None,
        user_vars: dict[str, str] = None,
        **_,
    ) -> None:
        if draw_item:
            self.draw_item = draw_item
        if edit_item:
            self.edit_item = edit_item
        if split:
            self.Splitter.SetSashPosition(split)
        if user_vars:
            self.user_vars = user_vars

    def ReloadLists(self) -> None:
        self.core.clear_cache()
        draw_selection = self.DrawItem.GetStringSelection()
        items = {}

        for board_name in self.core.list_json("boards"):
            items[f"Board - {board_name}"] = f"boards/{board_name}"
        for template_name in self.core.list_json("templates"):
            items[f"Template - {template_name}"] = f"templates/{template_name}"
        for shape_name in self.core.list_json("shapes"):
            items[f"Shape - {shape_name}"] = f"shapes/{shape_name}"

        self.DrawItem.SetItems(sorted(items.keys()))
        self.DrawItem.SetStringSelection(draw_selection)
        self.draw_items = items

    def OnUpdate(self, target: wx.Window = None) -> None:
        super().OnUpdate(target)
        if not self.IsShown():
            return
        match target:
            case self.DrawItem:
                self.Svg.ClearSvg()
                self.UpdateDrawItem()
            case self.EditItem:
                self.UpdateEditItem()

            case _:
                # debug(f"OnUpdate({target})")
                pass

    def UpdateDrawItem(self, force_list: bool = True) -> None:
        item = self.draw_item
        if not item:
            return
        item_type, _, item_name = item.partition("/")

        self.edit_items = {}
        obj: dict = {}
        try:
            match item_type:
                case "boards":
                    obj = self.core.load_board(item_name, allow_cache=False)
                case "templates":
                    obj = self.core.load_template(item_name)
                case "shapes":
                    obj = self.core.load_shape(item_name)
        except Exception as e:
            self.SetError(e)
            if force_list:
                self.FillEditList()
            return
        self.vars = obj["vars"] if "vars" in obj else {}
        parent = HasVars(vars=self.vars)

        try:
            match item_type:
                case "boards":
                    self.draw_object = self.core.get_board(item_name)

                case "templates":
                    front: list[Shape] = []
                    back: list[Shape] = []
                    template = Template(**obj)
                    for data in template.front:
                        shape = self.core.build_shape(parent=parent, data=data)
                        front.append(shape)
                    for data in template.back:
                        shape = self.core.build_shape(parent=parent, data=data)
                        back.append(shape)
                    if front and back:
                        self.draw_object = [
                            ShapeGroup.wrap(self.core, item_name, front),
                            ShapeGroup.wrap(self.core, item_name, back),
                        ]
                    elif front:
                        self.draw_object = ShapeGroup.wrap(self.core, item_name, front)
                    elif back:
                        self.draw_object = ShapeGroup.wrap(self.core, item_name, back)

                case "shapes":
                    shapes: list[Shape] = []
                    for data in obj:
                        shape = self.core.build_shape(parent=parent, data=data)
                        shapes.append(shape)
                    self.draw_object = ShapeGroup.wrap(self.core, item_name, shapes)

            self.Redraw()
            self.SetError(None)
        except Exception as e:
            self.SetError(e)
            if not force_list:
                return
        self.FillEditList()

    def FillEditList(self) -> None:
        selection = self.EditItem.GetStringSelection()
        self.EditItem.Clear()
        self.EditItem.Append(list(self.edit_items.keys()))
        self.EditItem.Enable(True)
        self.EditItem.SetStringSelection(selection)

        if not self.EditItem.GetStringSelection():
            if self.EditItem.GetItems():
                self.edit_item = self.EditItem.GetItems()[0]
            else:
                self.Data.Clear()
                self.Path.Clear()

    def AddEditItem(self, type: str, name: str, data: dict, file: str | None) -> None:
        key = f"{type} -> {name}".replace("\\", "/")
        value = f"{type}/{name}", data
        self.edit_items[key] = value
        if file:
            file = abspath(file)
            self.file_map[value[0]] = file

    def UpdateEditItem(self) -> None:
        item = self.edit_item
        if not item:
            return
        item_name, obj = item
        self.edit_selection = item_name
        scroll_pos = self.Data.GetScrollPos(wx.VERTICAL)
        cursor_pos = self.Data.GetInsertionPoint()
        self.Data.ChangeValue(json.dumps(obj, indent=4))
        self.Data.SetInsertionPoint(cursor_pos)
        self.Data.SetScrollPos(wx.VERTICAL, scroll_pos)
        self.Format.Enable(True)
        self.Revert.Enable(item_name in self.modified)
        self.UpdateDataPosition()
        if "pcb" in obj:
            obj = obj["pcb"]
        self.vars = obj["vars"] if "vars" in obj else {}

    def Redraw(self) -> None:
        debug(f"Draw object: {self.draw_object}")
        match self.draw_object:
            case Board():
                images = get_pcb_images(
                    self.core,
                    self.draw_object.pcb,
                    with_labels=True,
                )
            case list():
                images = self.draw_object
            case Shape():
                images = [self.draw_object]
            case _:
                return
        if not images:
            self.Svg.ClearSvg()
            return
        dwg = draw_shapes(V(1024, 500), 12, images, with_canvas=False)
        self.Svg.LoadSvg(dwg.tostring())

    @with_event
    def OnDataText(self, event: wx.Event) -> None:
        event.Skip()
        try:
            text = self.Data.GetValue()
            obj = json.loads(text)
            if obj:
                self.data = obj
                if self.edit_item:
                    self.MarkModified()
            self.edit_errors = False
            self.UpdateDrawItem(force_list=self.edit_path.startswith("_base"))
        except json.JSONDecodeError:
            self.edit_errors = True

    @with_event
    def OnVarsText(self, event: wx.Event) -> None:
        event.Skip()
        self.UpdateDrawItem()

    @with_event
    def OnDataPosition(self, event: wx.Event) -> None:
        event.Skip()
        self.UpdateDataPosition()

    def UpdateDataPosition(self) -> None:
        text = self.Data.GetValue()
        text = text.replace("\n", "\r\n")
        pos = max(0, self.Data.GetInsertionPoint() - 1)
        self.edit_path = jsonpath(text, pos) or ""
        if self.edit_path:
            self.Path.ChangeValue(self.edit_path.replace(".", " -> "))
        else:
            self.Path.ChangeValue("")
        self.UpdateEditType()

    @on_event
    def OnSaveClick(self) -> None:
        self.Modified.SetLabel("Modified: 0")
        self.Save.Enable(False)
        self.Discard.Enable(False)
        self.Revert.Enable(False)
        if not self.modified:
            return
        for file, obj in self.modified.items():
            path = self.file_map.get(file, None)
            if not path:
                warning(f"Couldn't save '{file}' - path is unknown")
                continue
            with open(path, "w", encoding="utf-8") as f:
                json.dump(obj, f, indent="\t")
                f.write("\n")
        info(f"Saved {len(self.modified)} files")
        self.modified.clear()

    @on_event
    def OnDiscardClick(self) -> None:
        self.Modified.SetLabel("Modified: 0")
        self.Save.Enable(False)
        self.Discard.Enable(False)
        self.Revert.Enable(False)
        if not self.modified:
            return
        self.modified.clear()
        self.core.clear_cache()
        self.UpdateDrawItem()
        self.UpdateEditItem()

    @on_event
    def OnRevertClick(self) -> None:
        self.MarkUnmodified()
        name, _ = self.edit_item
        item_type, _, item_name = name.partition("/")
        self.core.remove_from_cache(item_type, item_name)
        self.UpdateDrawItem()
        self.UpdateEditItem()

    @on_event
    def OnModifiedClick(self) -> None:
        if not self.modified:
            message = "No files have been modified"
        else:
            message = "The following files have been modified:\n\n"
            for file in sorted(self.modified.keys()):
                path = self.file_map.get(file, file)
                message += path + "\n"
        wx.MessageBox(message, "Information")

    @on_event
    def OnFormatClick(self) -> None:
        if self.edit_errors:
            wx.MessageBox(
                "Can't beautify, the JSON has syntax errors",
                "Error",
                wx.OK | wx.CENTRE | wx.ICON_ERROR,
            )
            return
        self.UpdateEditItem()

    @on_event
    def OnEditClick(self) -> None:
        bar: wx.MenuBar = self.Xrc.LoadMenuBar("EditMenuBar")
        menu: wx.Menu = bar.GetMenu(0)
        menu.Detach()
        if not self.draw_item:
            menu.FindItemByPosition(1).Enable(False)
            menu.FindItemByPosition(2).Enable(False)
            menu.FindItemByPosition(3).Enable(False)
        choice = self.Edit.GetPopupMenuSelectionFromUser(menu)
        item: wx.MenuItem = menu.FindItemById(choice)
        if not item:
            return
        label = item.GetItemLabel()
        parent_label = None

        owner_menu: wx.Menu = item.GetMenu()
        owner_menu_parent: wx.Menu = owner_menu.GetParent()
        if owner_menu_parent:
            for item in owner_menu_parent.GetMenuItems():
                if item.GetSubMenu() == owner_menu:
                    parent_label = item.GetItemLabel()
                    break

        match parent_label, label:
            case "Board...", "LibreTiny directory":
                self.CreateNewFile("boards", self.lvm.path(), INIT_BOARD)
            case "Board...", "boardgen directory":
                self.CreateNewFile("boards", self.core.dir_base, INIT_BOARD)

            case "Board base...", "LibreTiny directory":
                new_name = self.AskFileName()
                new_path = join(
                    self.lvm.path(),
                    "boards",
                    "_base",
                    f"{new_name}.json",
                )
                makedirs(dirname(new_path), exist_ok=True)
                with open(new_path, "w") as f:
                    f.write("{}\n")
            case "Board base...", "boardgen directory":
                new_name = self.AskFileName()
                new_path = join(
                    self.core.dir_base,
                    "boards",
                    "_base",
                    f"{new_name}.json",
                )
                makedirs(dirname(new_path), exist_ok=True)
                with open(new_path, "w") as f:
                    f.write("{}\n")

            case "Template...", "LibreTiny directory":
                boards_dir = join(self.lvm.path(), "boards")
                self.CreateNewFile("templates", boards_dir, INIT_TEMPLATE)
            case "Template...", "boardgen directory":
                self.CreateNewFile("templates", self.core.dir_base, INIT_TEMPLATE)

            case "Shape...", "LibreTiny directory":
                boards_dir = join(self.lvm.path(), "boards")
                self.CreateNewFile("shapes", boards_dir, INIT_SHAPE)
            case "Shape...", "boardgen directory":
                self.CreateNewFile("shapes", self.core.dir_base, INIT_SHAPE)

            case _:
                if self.modified:
                    wx.MessageBox("Please save the changes first", "Information")
                    return
                if not self.edit_item:
                    return
                draw_item = self.draw_item
                old_path = self.file_map.get(draw_item, None)
                if not old_path:
                    return
                path_dir = dirname(old_path)
                old_name = basename(old_path).rpartition(".")[0]
                match label:
                    case "Rename item":
                        new_name = self.AskFileName(old_name)
                        if not new_name:
                            return
                        new_path = join(path_dir, f"{new_name}.json")
                        rename(old_path, new_path)
                        self.ReloadLists()
                        self.draw_item = draw_item.replace(old_name, new_name)
                    case "Delete item":
                        choice = wx.MessageBox(
                            f"Do you really want to delete '{draw_item}'?",
                            "Are you sure?",
                            wx.YES_NO | wx.ICON_QUESTION,
                        )
                        if choice != wx.YES:
                            return
                        unlink(old_path)
                        self.ReloadLists()
                        self.draw_item = self.DrawItem.GetItems()[0]
                    case "Duplicate item":
                        new_name = self.AskFileName(old_name)
                        if not new_name or new_name == old_name:
                            return
                        new_path = join(path_dir, f"{new_name}.json")
                        copyfile(old_path, new_path)
                        self.ReloadLists()
                        self.draw_item = draw_item.replace(old_name, new_name)

    def UpdateEditType(self) -> None:
        prev_type = self.edit_type
        if not self.edit_item:
            return
        name, _ = self.edit_item
        path = self.edit_path

        self.edit_type = None
        is_shape = (
            name.startswith("templates")
            and (path.startswith("front") or path.startswith("back"))
            or name.startswith("boards")
            and (path.startswith("pcb.front") or path.startswith("pcb.back"))
            or name.startswith("shapes")
        )
        is_vars = "vars." in path

        if is_shape and path.endswith(".name"):
            self.edit_type = EditType.SHAPE
        elif is_shape and path.endswith(".preset"):
            self.edit_type = EditType.PRESET
        elif is_vars and path.endswith("_PRESET"):
            self.edit_type = EditType.PRESET
        elif is_vars and path.endswith("_COLOR"):
            self.edit_type = EditType.COLOR
        elif is_vars and ".PINTYPE" in path:
            self.edit_type = EditType.SHAPE
        elif path.endswith(".color"):
            self.edit_type = EditType.COLOR
        elif path.endswith(".lgrad.1") or path.endswith(".lgrad.3"):
            self.edit_type = EditType.COLOR
        elif path.endswith(".family"):
            self.edit_type = EditType.FAMILY
        elif path.startswith("connectivity"):
            self.edit_type = EditType.CONNECTIVITY
        elif path.startswith("pcb.pinout.") or path.startswith("pcb.ic."):
            self.edit_type = EditType.ROLE
        elif path.startswith("pcb.pinout_hidden"):
            self.edit_type = EditType.ROLE_HIDDEN
        elif path.startswith("flash"):
            self.edit_type = EditType.FLASH
        elif path.startswith("pcb.templates"):
            self.edit_type = EditType.TEMPLATE
        elif is_shape:
            self.edit_type = EditType.SHAPE_ADD
        elif name.startswith("boards") and "_base" not in name:
            self.edit_type = EditType.BASE

        if self.edit_type:
            self.Choose.Enable(True)
            self.Choose.SetLabel(self.edit_type.name.replace("_", " ").title() + "...")
        else:
            self.Choose.Enable(False)
        if self.edit_type != prev_type:
            debug(f"Chooser type: {self.edit_type}")

    @on_event
    def OnChooseClick(self) -> None:
        if self.edit_errors:
            wx.MessageBox(
                "Can't do this, the JSON has syntax errors",
                "Error",
                wx.OK | wx.CENTRE | wx.ICON_ERROR,
            )
            return
        data = self.data
        if data is None:
            return
        path = self.edit_path

        if self.edit_type == EditType.SHAPE_ADD:
            # special case for adding shapes - find the shape list
            parts = path.split(".")
            new_path = []
            for part in parts:
                if part.isnumeric():
                    break
                new_path.append(part)
            if new_path:
                path = ".".join(new_path)
            elif isinstance(data, list):
                # path starts with numeric value - data object is a list
                path = parts[0]

        walk = jsonwalk(data, path)
        if not walk:
            return
        parent, key = walk
        this_value = parent[key]
        this_dict = this_value if isinstance(this_value, dict) else parent
        this_list = parent if isinstance(parent, list) else this_value
        new_value: str | int | None = None
        new_dict: dict | None = None
        new_list: list | None = None

        match self.edit_type:
            # multiple choice
            case EditType.BASE:
                items = self.core.list_json("boards", recursive=True)
                items = [i[6:] for i in items if i.startswith("_base/")]
                items = sorted(items, key=lambda i: "_" + i if "/" not in i else i)
                data["_base"] = self.AskMultipleChoice(
                    title="Choose board base",
                    items=items,
                    selected=data.get("_base", []),
                    sort=False,
                )
            case EditType.TEMPLATE:
                items = self.core.list_json("templates")
                items = sorted(items)
                new_list = self.AskMultipleChoice(
                    title="Choose PCB templates",
                    items=items,
                    selected=this_list,
                )
            case EditType.CONNECTIVITY:
                new_list = self.AskMultipleChoice(
                    title="Choose module connectivity options",
                    items=["wifi", "ble"],
                    selected=this_list,
                    sort=False,
                )
            case EditType.ROLE_HIDDEN:
                roles = self.AskMultipleChoice(
                    title="Choose hidden pinout roles",
                    items=[i.name for i in self.core.roles.keys()],
                    selected=this_value.split(","),
                    anchor=self.Choose,
                )
                new_value = ",".join(roles)
            # single choice
            case EditType.SHAPE:
                items = self.core.list_json("shapes")
                items = sorted(items)
                new_value = self.AskSingleChoice(
                    title="Choose shape",
                    items=items,
                    selected=this_value,
                    anchor=self.Choose,
                )
            case EditType.SHAPE_ADD:
                shape_type = self.AskSingleChoice(
                    title="Choose shape type to add",
                    items=[i.name.lower() for i in self.core.shape_ctors.keys()],
                    anchor=self.Choose,
                )
                default = {"type": shape_type}
                shape = SHAPE_DEFAULTS.get(shape_type, default)
                this_list.append(deepcopy(shape))
            case EditType.PRESET:
                new_value = self.AskSingleChoice(
                    title="Choose shape preset",
                    items=list(self.core.presets.keys()),
                    selected=this_value,
                    anchor=self.Choose,
                )
            case EditType.FAMILY:
                new_value = self.AskSingleChoice(
                    title="Choose chip family",
                    items=[f.short_name for f in Family.get_all() if f.is_chip],
                    selected=this_value,
                    sort=False,
                    anchor=self.Choose,
                )
            case EditType.ROLE:
                roles = set(i.name for i in self.core.roles.keys())
                roles.update(ROLE_DEFAULTS.keys())
                roles = sorted(roles)
                roles.remove("IC")
                roles.insert(0, "IC")
                role = self.AskSingleChoice(
                    title="Choose pin role to add",
                    items=roles,
                    sort=False,
                    anchor=self.Choose,
                )
                if not role:
                    return
                role_value = ROLE_DEFAULTS.get(role, "")
                if (
                    role == "IC"
                    and self.draw_item.startswith("boards/")
                    and self.draw_object
                    and self.draw_object.pcb
                    and self.draw_object.pcb.ic
                ):
                    ic_pins = {}
                    for ic_pin, role_map in self.draw_object.pcb.ic.items():
                        pin_roles = []
                        for role_type, functions in role_map.items():
                            if role_type == RoleType.IO:
                                continue
                            role_obj = self.core.role(role_type)
                            if not role_obj:
                                continue
                            pin_roles += role_obj.format(functions, long=False)
                        ic_pins[" / ".join(pin_roles)] = ic_pin
                    ic_role = self.AskSingleChoice(
                        title="Choose pin to add",
                        items=list(ic_pins.keys()),
                        anchor=self.Choose,
                    )
                    if not ic_role:
                        return
                    role_value = ic_pins[ic_role]
                ex_roles = ["PWR", "GND", "NC"]
                for ex_role in ex_roles:
                    if role == ex_role:
                        this_dict.clear()
                    else:
                        this_dict.pop(ex_role, None)
                this_dict[role] = role_value
            case EditType.FLASH:
                region = self.AskSingleChoice(
                    title="Choose flash region to add",
                    items=list(self.core.flash.keys()),
                    anchor=self.Choose,
                )
                if region not in this_dict:
                    this_dict[region] = "0x000000+0x0000"
            # other
            case EditType.COLOR:
                cdata = wx.ColourData()
                cdata.SetChooseFull(True)
                cdata.SetChooseAlpha(False)
                cdata.SetColour(this_value)
                dialog = wx.ColourDialog(
                    self,
                    data=cdata,
                )
                if dialog.ShowModal() == wx.ID_OK:
                    cdata = dialog.GetColourData()
                    color: wx.Colour = cdata.GetColour()
                    new_value = color.GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
                    new_value = new_value.replace(" ", "")
                dialog.Destroy()

        if new_value and new_value != this_value and isinstance(parent, (dict, list)):
            parent[key] = new_value
        elif new_dict and new_dict is not this_dict:
            this_dict.clear()
            this_dict.update(new_dict)
        elif new_list and new_list is not this_list:
            this_list.clear()
            this_list += new_list
        self.UpdateEditItem()
        self.UpdateDrawItem()
        self.MarkModified()

    def AskFileName(self, value: str = "") -> str | None:
        dialog = wx.TextEntryDialog(
            self,
            message="Enter the new file name (without .json):",
            caption="File name",
            value=value,
        )
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return
        value = dialog.GetValue().strip()
        dialog.Destroy()
        return value

    def AskMultipleChoice(
        self,
        title: str,
        items: list[str],
        selected: list[str],
        sort: bool = True,
        anchor: wx.Window = None,
    ) -> list[str]:
        if sort:
            items = sorted(items)
        choice = []
        missing = []
        for item in selected[::-1]:
            if item not in items:
                missing.insert(0, item)
                continue
            items.remove(item)
            items.insert(0, item)

        if anchor:
            menu = wx.Menu()
            for item in items:
                menu_item: wx.MenuItem = menu.AppendCheckItem(wx.ID_ANY, item)
                menu_item.Check(item in selected)
            if anchor.PopupMenu(menu, 0, 25):
                choice = [
                    items[idx]
                    for idx, item in enumerate(menu.GetMenuItems())
                    if item.IsChecked()
                ]
            menu.Destroy()
        else:
            dialog = wx.MultiChoiceDialog(
                self,
                message=title,
                caption="Choose items",
                choices=items,
            )
            if selected:
                dialog.SetSelections([items.index(i) for i in selected if i in items])
            if dialog.ShowModal() == wx.ID_OK:
                choice = [items[i] for i in dialog.GetSelections()]
            dialog.Destroy()

        return choice + missing if choice else selected

    def AskSingleChoice(
        self,
        title: str,
        items: list[str],
        selected: str | None = None,
        sort: bool = True,
        anchor: wx.Window = None,
    ) -> str:
        if sort:
            items = sorted(items)
        choice = None

        if anchor:
            menu = wx.Menu()
            if selected:
                for item in items:
                    menu_item: wx.MenuItem = menu.AppendRadioItem(wx.ID_ANY, item)
                    menu_item.Check(item == selected)
                if anchor.PopupMenu(menu, 0, 25):
                    choice = next(
                        items[idx]
                        for idx, item in enumerate(menu.GetMenuItems())
                        if item.IsChecked()
                    )
            else:
                for item in items:
                    menu.Append(wx.ID_ANY, item)
                selection = anchor.GetPopupMenuSelectionFromUser(menu, 0, 25)
                if selection != -1:
                    for i, item in enumerate(items):
                        if menu.FindItemByPosition(i).GetId() == selection:
                            choice = item
                            break
            menu.Destroy()
        else:
            dialog = wx.SingleChoiceDialog(
                self,
                message=title,
                caption="Choose items",
                choices=items,
            )
            if selected in items:
                dialog.SetSelection(items.index(selected))
            if dialog.ShowModal() == wx.ID_OK:
                choice = (
                    items[dialog.GetSelection()]
                    if dialog.GetSelection() != -1
                    else None
                )
            dialog.Destroy()

        return choice or selected

    def CreateNewFile(self, item_type: str, directory: str, value: dict | list) -> None:
        name = self.AskFileName()
        if not name:
            return

        if value is INIT_BOARD:
            value["build"]["variant"] = name
            value["name"] = name
        if value is INIT_TEMPLATE:
            value["name"] = name
            value["title"] = name

        makedirs(join(directory, item_type), exist_ok=True)
        with open(join(directory, item_type, f"{name}.json"), "w") as f:
            json.dump(value, f, indent="\t")
            f.write("\n")
        self.ReloadLists()
        self.draw_item = f"{item_type}/{name}"
        self.Svg.ClearSvg()
        self.UpdateDrawItem()

    def SetError(self, e: Exception | None) -> None:
        if not e:
            self.Error.Clear()
        else:
            self.Error.SetValue(f"{type(e).__name__}: {e}")

    def MarkModified(self) -> None:
        if not self.edit_item:
            return
        file, obj = self.edit_item
        if file in self.modified:
            return
        self.modified[file] = obj
        self.Modified.SetLabel(f"Modified: {len(self.modified)}")
        self.Save.Enable(True)
        self.Discard.Enable(True)
        self.Revert.Enable(True)

    def MarkUnmodified(self) -> None:
        if not self.edit_item:
            return
        file, obj = self.edit_item
        if file not in self.modified:
            return
        self.modified.pop(file)
        self.Modified.SetLabel(f"Modified: {len(self.modified)}")
        self.Save.Enable(len(self.modified) > 0)
        self.Discard.Enable(len(self.modified) > 0)
        self.Revert.Enable(False)

    @property
    def user_vars(self) -> dict[str, str]:
        lines: list[str] = self.Vars.GetValue().splitlines()
        data = {}
        for line in lines:
            key, _, value = line.strip().partition("=")
            data[key] = value
        return data

    @user_vars.setter
    def user_vars(self, value: dict[str, str]) -> None:
        self.Vars.SetValue("\n".join(f"{k}={v}" for k, v in value.items()))

    @property
    def vars(self) -> dict[str, str]:
        data = self.user_vars
        data |= self._vars
        return data

    @vars.setter
    def vars(self, value: dict[str, str]) -> None:
        self._vars.clear()
        self._vars.update(value)

    @property
    def draw_item(self) -> str | None:
        return self.draw_items.get(self.DrawItem.GetStringSelection(), None)

    @draw_item.setter
    def draw_item(self, value: str) -> None:
        for key, item in self.draw_items.items():
            if key == value or item == value:
                self.DrawItem.SetStringSelection(key)
                self.UpdateDrawItem()
                return

    @property
    def edit_item(self) -> tuple[str, dict] | None:
        return self.edit_items.get(self.EditItem.GetStringSelection(), None)

    @edit_item.setter
    def edit_item(self, value: str) -> None:
        for key, item in self.edit_items.items():
            if key == value or item[1] == value == value:
                self.EditItem.SetStringSelection(key)
                self.UpdateEditItem()
                return

    @property
    def data(self) -> dict | None:
        item = self.edit_item
        return item and item[1]

    @data.setter
    def data(self, value: dict) -> None:
        data = self.data
        if data is None:
            return
        debug(f"Data change, id={id(data)}")
        data.clear()
        if isinstance(data, dict):
            data.update(value)
        if isinstance(data, list):
            data += value
