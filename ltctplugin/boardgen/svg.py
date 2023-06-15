#  Copyright (c) Kuba Szczodrzyński 2023-6-3.

import wx
import wx.svg


class SvgPanel(wx.Control):
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

    def LoadSvg(self, svg: str) -> None:
        self.Image = wx.svg.SVGimage.CreateFromBytes(svg.encode())
        self.Refresh(False)

    def OnPaint(self, event) -> None:
        size = self.GetClientSize()
        dc = wx.BufferedPaintDC(self)
        dc.Clear()

        if not self.Image:
            return

        dcdim = min(size.width, size.height * 2)
        imgdim = max(self.Image.width, self.Image.height)
        scale = dcdim / imgdim
        int(self.Image.width * scale)
        int(self.Image.height * scale)

        r: wx.GraphicsRenderer = wx.GraphicsRenderer.GetDirect2DRenderer()
        ctx = r.CreateContext(dc)
        self.Image.RenderToGC(ctx, scale)

    def OnSize(self, event) -> None:
        self.Refresh(False)

    def OnEraseBackground(self, event) -> None:
        pass
