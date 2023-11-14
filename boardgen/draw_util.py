#  Copyright (c) Kuba Szczodrzyński 2023-6-3.

from svgwrite import Drawing, shapes
from svgwrite.utils import AutoID

from .core import Core
from .models import Pcb, Side
from .shapes import Shape, ShapeGroup
from .vector import V


def get_pcb_images(core: Core, pcb: Pcb, with_labels: bool) -> list[Shape]:
    shapes = []
    for side in [Side.FRONT, Side.BACK]:
        shape = pcb.shapes[side]
        if with_labels:
            labels, _, _ = core.build_labels(pcb, side)
            if labels:
                shapes.append(ShapeGroup.wrap(core, side.value, [shape] + labels))
        else:
            shapes.append(shape)
    return shapes


def draw_shapes(
    px_size: V,
    scale: float | None,
    images: list[Shape],
    with_canvas: bool,
    rescale_viewbox: bool = True,
) -> Drawing:
    AutoID._set_value(1)
    dwg = Drawing(size=px_size.tuple)

    # stack horizontally
    shape_size = [shape.size for shape in images]
    total_size = sum(s.x for s in shape_size)
    part_size = [
        V(px_size.x * (shape_size[i].x / total_size), px_size.y)
        for i in range(len(images))
    ]
    part_pos = [V(sum(s.x for s in part_size[0:i]), 0) for i in range(len(images))]

    if scale:
        vb_size = px_size / scale
    else:
        scale = 99999
        for i in range(len(images)):
            size_pad = part_size[i] * 0.90  # 5% padding from each side
            size = shape_size[i]
            scale = min(scale, size_pad.x / size.x, size_pad.y / size.y)
        print(" - calculated scale: %.2f" % scale)
        vb_size = px_size / scale

    if rescale_viewbox:
        dwg.viewbox(width=px_size.x, height=px_size.y)
        unit = scale
    else:
        dwg.viewbox(width=vb_size.x, height=vb_size.y)
        unit = 1.0

    if with_canvas:
        bg = shapes.Rect(insert=(0, 0), size=(vb_size * unit).tuple)
        bg.fill(color="white")
        bg.stroke(color="black", width=0.1 * unit)
        dwg.add(bg)

    for i, shape in enumerate(images):
        shape_pos = ((part_size[i] / scale) - shape_size[i]) / 2
        shape_pos += part_pos[i] / scale
        shape_pos -= shape.pos1
        if with_canvas:
            shape_pos.x -= 0.05
        shape.move(shape_pos)
        shape.draw(dwg, unit=unit)
        shape.move(-shape_pos)

    return dwg
