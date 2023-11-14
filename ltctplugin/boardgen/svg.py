#  Copyright (c) Kuba Szczodrzyński 2023-6-3.

import wx
import wx.svg
from svgwrite import Drawing
from svgwrite.base import BaseElement
from svgwrite.container import Group
from svgwrite.text import Text


class SvgPanel(wx.Control):
    Svg: Drawing | None = None
    Image: wx.svg.SVGimage | None = None

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def ClearSvg(self) -> None:
        self.Image = None
        self.Refresh(False)

    def LoadSvg(self, svg: Drawing) -> None:
        self.Svg = svg
        self.Image = wx.svg.SVGimage.CreateFromBytes(svg.tostring().encode())
        self.Refresh(False)

    def OnPaint(self, event) -> None:
        size = self.GetClientSize()
        dc = wx.BufferedPaintDC(self)
        dc.Clear()

        if not self.Image:
            return

        # calculate svg -> viewport scale
        dcdim = min(size.width, size.height * 2)
        imgdim = max(self.Image.width, self.Image.height)
        scale = dcdim / imgdim

        r: wx.GraphicsRenderer = wx.GraphicsRenderer.GetDirect2DRenderer()
        ctx: wx.GraphicsContext = r.CreateContext(dc)
        self.Image.RenderToGC(ctx, scale)

        if not self.Svg:
            return

        # adjust scale for viewBox units
        _, _, vb_width, vb_height = self.Svg["viewBox"].split(",")
        scale *= self.Image.width / float(vb_width)

        self.DrawSvgText(ctx, self.Svg.elements, scale)

    def DrawSvgText(
        self,
        ctx: wx.GraphicsContext,
        elements: list[BaseElement],
        scale: float = 1.0,
    ) -> None:
        for element in elements:
            if isinstance(element, Group):
                self.DrawSvgText(ctx, element.elements)
                continue
            if not isinstance(element, Text):
                continue

            text_size = float(element.attribs["font-size"])
            char_width = 23 / 40 * text_size  # approximate size that looks good
            text_x = float(element.attribs["x"])
            text_y = float(element.attribs["y"])
            if element.attribs.get("text-anchor", None) == "middle":
                text_x -= len(element.text) * char_width / 2
            if element.attribs.get("dominant-baseline", None) in ["central", "middle"]:
                text_y -= text_size / 2
            else:
                text_y -= text_size

            font: wx.GraphicsFont = ctx.CreateFont(
                sizeInPixels=text_size * scale,
                facename=element.attribs["font-family"],
                col=element.attribs["fill"],
            )
            ctx.SetFont(font)
            ctx.DrawText(
                str=element.text,
                x=text_x * scale,
                y=text_y * scale,
            )

    def OnSize(self, event) -> None:
        self.Refresh(False)

    def OnEraseBackground(self, event) -> None:
        pass
