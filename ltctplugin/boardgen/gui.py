#  Copyright (c) Kuba Szczodrzyński 2023-6-3.

import json
from dataclasses import dataclass
from logging import debug
from os.path import join

import wx
import wx.adv
import wx.xrc
from ltchiptool.gui.panels.base import BasePanel
from ltchiptool.gui.utils import with_event
from ltchiptool.util.lvm import LVM

from boardgen import Core, HasVars, V
from boardgen.draw_util import draw_shapes, get_pcb_images
from boardgen.models import Board, Template
from boardgen.shapes import Shape, ShapeGroup

from .svg import SvgPanel
from .utils import jsonpath


@dataclass
class EditableShape:
    prefix: str
    data: dict
    shape: Shape = None

    @staticmethod
    def build(core: Core, _vars: dict, data: dict) -> "EditableShape":
        _vars |= {"DUMMY": 0}
        obj = EditableShape(
            prefix="",
            data=data,
        )
        obj.rebuild(core, _vars)
        return obj

    def rebuild(self, core: Core, _vars: dict) -> None:
        self.shape = core.build_shape(parent=HasVars(vars=_vars), data=self.data)

    @property
    def title(self) -> str:
        title = self.prefix + type(self.shape).__name__ + str(self.shape.pos.tuple)
        if self.shape.id:
            title += " - " + self.shape.id
        if isinstance(self.shape, ShapeGroup):
            title = "Shape - " + self.shape.name
        return title


class BoardgenPanel(BasePanel):
    file_map: dict[str, str] = None
    draw_items: dict[str, tuple[str, str]] = None
    draw_object: Board | list[Shape] | Shape
    edit_items: dict[str, tuple[str, dict]] = None
    edit_selection: str = None
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
        self.Modified: wx.adv.HyperlinkCtrl = self.BindWindow(
            "label_modified",
            (wx.adv.EVT_HYPERLINK, self.OnModifiedClick),
        )

        self.lvm = LVM.get()
        self.core = Core()
        self.core.add_custom_dirs(boards=join(self.lvm.path(), "boards"))
        self.core.json_hook = self.AddEditItem

        self.file_map = {}
        self.draw_items = {}
        self.edit_items = {}
        self.modified = {}

        self.ReloadLists()

    def GetSettings(self) -> dict:
        return dict()

    def SetSettings(
        self,
        **_,
    ) -> None:
        pass

    def ReloadLists(self) -> None:
        draw_selection = self.DrawItem.GetStringSelection()
        items = {}

        for board_name in self.core.list_json("boards"):
            board = self.core.load_board(board_name)
            items[f"Board - {board['name']}"] = "board", board_name
        for template_name in self.core.list_json("templates"):
            template = self.core.load_template(template_name)
            items[f"Template - {template['title']}"] = "template", template_name
        for shape_name in self.core.list_json("shapes"):
            # shape = self.core.load_shape(shape_name)
            items[f"Shape - {shape_name}"] = "shape", shape_name

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
                self.UpdateDrawItem(force_list=True)
            case self.EditItem:
                self.UpdateEditItem()

            case _:
                # debug(f"OnUpdate({target})")
                pass

    def UpdateDrawItem(self, force_list: bool = False) -> None:
        item_type, item_name = self.draw_item

        self.edit_items = {}
        obj: dict = {}
        try:
            match item_type:
                case "board":
                    obj = self.core.load_board(item_name, allow_cache=False)
                case "template":
                    obj = self.core.load_template(item_name)
                case "shape":
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
                case "board":
                    self.draw_object = self.core.get_board(item_name)

                case "template":
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

                case "shape":
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
        item_name, obj = self.edit_item
        self.edit_selection = item_name
        self.Data.ChangeValue(json.dumps(obj, indent=4))
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
            self.UpdateDrawItem(force_list=self.edit_path.startswith("_base"))
        except json.JSONDecodeError:
            return

    @with_event
    def OnVarsText(self, event: wx.Event) -> None:
        event.Skip()
        self.UpdateDrawItem()

    @with_event
    def OnDataPosition(self, event: wx.Event) -> None:
        event.Skip()
        text = self.Data.GetValue()
        text = text.replace("\n", "\r\n")
        pos = max(0, self.Data.GetInsertionPoint() - 1)
        self.edit_path = jsonpath(text, pos) or ""
        if self.edit_path:
            self.Path.ChangeValue(self.edit_path.replace(".", " -> "))
        else:
            self.Path.ChangeValue("")

    @on_event
    def OnSaveClick(self) -> None:
        self.Modified.SetLabel("Modified: 0")
        self.Save.Enable(False)
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
    def OnModifiedClick(self) -> None:
        if not self.modified:
            message = "No files have been modified"
        else:
            message = "The following files have been modified:\n\n"
            for file in sorted(self.modified.keys()):
                path = self.file_map.get(file, file)
                message += path + "\n"
        wx.MessageBox(message, "Information")

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

    @property
    def vars(self) -> dict[str, str]:
        lines: list[str] = self.Vars.GetValue().splitlines()
        data = {}
        for line in lines:
            key, _, value = line.strip().partition("=")
            data[key] = value
        data |= self._vars
        return data

    @vars.setter
    def vars(self, value: dict[str, str]) -> None:
        self._vars = value

    @property
    def draw_item(self) -> tuple[str, str] | None:
        return self.draw_items.get(self.DrawItem.GetStringSelection(), None)

    @draw_item.setter
    def draw_item(self, value: str) -> None:
        for key, item in self.draw_items.items():
            if key == value or item[1] == value:
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
