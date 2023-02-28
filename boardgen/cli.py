# Copyright (c) Kuba Szczodrzyński 2022-05-09.

import os
from os.path import join

import click
from click import echo
from devtools import debug
from svgwrite import Drawing, shapes
from svgwrite.utils import AutoID

from . import Core
from .models import Board, Side, Template
from .readme.writer import ReadmeWriter
from .shapes.label import Label
from .utils import load_json
from .variant.writer import VariantWriter
from .vector import V

core = Core()


def load_boards(boards: list[str | Board]) -> list[Board]:
    if not boards:
        return boards
    if isinstance(boards[0], str):
        if boards[0] == "all":
            boards = core.list_json("boards")
        boards = [
            echo(f"Loading board '{board}'...") or core.get_board(board)
            for board in boards
        ]
    return boards


@click.group(help=f"boardgen CLI v{core.version}")
@click.option("--boards", type=str, multiple=True, help="Custom boards directories")
@click.option("--shapes", type=str, multiple=True, help="Custom shapes directories")
@click.option(
    "--templates", type=str, multiple=True, help="Custom templates directories"
)
@click.option("--presets", type=str, multiple=True, help="Custom presets .json")
@click.option("--roles", type=str, multiple=True, help="Custom roles .json")
@click.option("--flash", type=str, multiple=True, help="Custom flash regions .json")
def cli(
    boards: tuple[str],
    shapes: tuple[str],
    templates: tuple[str],
    presets: tuple[str],
    roles: tuple[str],
    flash: tuple[str],
    *args,
    **kwargs,
):
    print(f"boardgen CLI v{core.version}")
    core.add_custom_dirs(
        boards=list(boards),
        shapes=list(shapes),
        templates=list(templates),
    )
    presets_data = {}
    roles_data = {}
    flash_data = {}
    for file in presets:
        presets_data |= load_json(file)
    for file in roles:
        roles_data |= load_json(file)
    for file in flash:
        flash_data |= load_json(file)
    core.add_custom_json(presets=presets_data, roles=roles_data, flash=flash_data)


@cli.command()
@click.argument("boards", nargs=-1, required=True)
@click.option("--dump", "-d", is_flag=True, help="Dump board info and exit")
@click.option("--output", "-o", default=".", help="Output directory")
@click.option("--subdir", "-O", is_flag=True, help="Output into per-board subdirectory")
@click.option("--width", "-w", default=1024, help="Image width (px)")
@click.option("--height", "-h", default=500, help="Image height (px)")
@click.option(
    "--scale",
    "-s",
    default=12,
    help="Diagram size (bigger if scale larger); 0 means automatic",
)
@click.option(
    "--canvas/--no-canvas",
    "-c/-C",
    default=True,
    help="Draw a white background with black border",
)
@click.option("--labels/--no-labels", "-l/-L", default=True, help="Draw pin labels")
@click.pass_context
def draw(
    ctx,
    boards: list[str],
    dump: bool,
    output: str,
    subdir: bool,
    width: int,
    height: int,
    scale: float,
    canvas: bool,
    labels: bool,
):
    """Draw board diagrams"""
    boards = load_boards(boards)
    if dump:
        for board in boards:
            debug(board)
        ctx.exit()

    px_size = V(width, height)

    if output:
        os.makedirs(output, exist_ok=True)

    sides = [Side.FRONT, Side.BACK]

    scale_arg = scale

    for board in boards:
        board: Board
        if not board.pcb or not board.pcb.templates:
            echo(f"Skipping '{board.name}'...")
            continue
        echo(f"Drawing '{board.name}'...")

        pcb = board.pcb
        images = []

        AutoID._set_value(1)
        dwg = Drawing(size=px_size.tuple)

        scale = scale_arg
        if pcb.scale and pcb.scale < scale:
            scale = pcb.scale

        for side in sides:
            try:
                (pcb_pos1, pcb_pos2) = pcb.get_pos(side)
            except ValueError:
                continue
            labels_list = []
            size = pcb_pos2 - pcb_pos1
            pos1 = pcb_pos1
            if labels:
                (labels_list, labels_pos1, labels_pos2) = core.build_labels(pcb, side)
                if labels_list:
                    pos1 = V(
                        min(pcb_pos1.x, labels_pos1.x), min(pcb_pos1.y, labels_pos1.y)
                    )
                    pos2 = V(
                        max(pcb_pos2.x, labels_pos2.x), max(pcb_pos2.y, labels_pos2.y)
                    )
                    size = pos2 - pos1
                else:
                    continue
            images += [
                (side, pos1, size, labels_list),
            ]

        # stack horizontally
        part_size = V(px_size.x / len(images), px_size.y)
        part_pos = [V(part_size.x * i, 0) for i in range(len(images))]

        if scale:
            vb_size = px_size / scale
        else:
            scale = 99999
            size_pad = part_size * 0.90  # 5% padding from each side
            for _, _, size, _ in images:
                scale = min(scale, size_pad.x / size.x, size_pad.y / size.y)
            echo(" - calculated scale: %.2f" % scale)
            vb_size = px_size / scale

        dwg.viewbox(width=vb_size.x, height=vb_size.y)

        if canvas:
            bg = shapes.Rect(insert=(0, 0), size=vb_size.tuple)
            bg.fill(color="white")
            bg.stroke(color="black", width=0.1)
            dwg.add(bg)

        for i, (side, pos1, size, labels_list) in enumerate(images):
            pcb_pos = ((part_size / scale) - size) / 2
            pcb_pos += part_pos[i] / scale
            pcb_pos -= pos1
            if canvas:
                pcb_pos.x -= 0.05
            pcb.draw(dwg, side, pcb_pos)
            if labels:
                for label in labels_list:
                    label: Label
                    label.move(pcb_pos)
                    label.draw(dwg)
                    label.move(-pcb_pos)

        svg = join(output, f"{board.id}.svg")
        if subdir:
            os.makedirs(join(output, board.id), exist_ok=True)
            svg = join(output, board.id, f"pinout_{board.id}.svg")
        with open(svg, "w", encoding="utf-8") as f:
            dwg.write(f, pretty=True, indent=4)


@cli.command()
@click.argument("boards", nargs=-1, required=True)
@click.option("--output", "-o", default=".", help="Output directory")
@click.option("--subdir", "-O", is_flag=True, help="Output into per-board subdirectory")
def write(
    boards: list[str],
    output: str,
    subdir: bool,
):
    """Write board README.md"""
    boards = load_boards(boards)

    if output:
        os.makedirs(output, exist_ok=True)

    for board in boards:
        board: Board
        readme = ReadmeWriter(core)
        readme.write(board=board)

        md = join(output, f"{board.id}.md")
        if subdir:
            md = join(output, board.id, f"README.md")

        echo(f"Saving to '{md}'...")
        readme.save(md)


@cli.command()
@click.argument("boards", nargs=-1, required=True)
@click.option("--output", "-o", default=".", help="Output directory")
@click.option("--subdir", "-O", is_flag=True, help="Output into per-board subdirectory")
def variant(
    boards: list[str],
    output: str,
    subdir: bool,
):
    """Write board variant definitions (.h/.cpp)"""
    boards = load_boards(boards)

    if output:
        os.makedirs(output, exist_ok=True)

    for board in boards:
        board: Board
        writer = VariantWriter(core)
        writer.generate(board=board)

        out_h = join(output, f"{board.id}.h")
        out_cpp = join(output, f"{board.id}.cpp")
        if subdir:
            out_h = join(output, board.id, f"variant.h")
            out_cpp = join(output, board.id, f"variant.cpp")

        echo(f"Saving to '{out_h}' and '{out_cpp}'...")
        board_name = f"{board.id}.json"
        writer.save_h(out_h, board_name)
        if writer.pins:
            writer.save_cpp(out_cpp, board_name)


@cli.command()
@click.argument("boards", nargs=-1, required=True)
@click.option("--output", "-o", default=".", help="Output directory")
@click.option("--subdir", "-O", is_flag=True, help="Output into per-board subdirectory")
@click.pass_context
def all(
    ctx,
    boards: list[str],
    output: str,
    subdir: bool,
):
    """Draw and generate complete board specifications"""
    boards = load_boards(boards)

    ctx.invoke(draw, boards=boards, output=output, subdir=subdir)
    ctx.invoke(write, boards=boards, output=output, subdir=subdir)
    ctx.invoke(variant, boards=boards, output=output, subdir=subdir)


@cli.group(name="list")
def list_cmd():
    """List boards/templates/etc"""


@list_cmd.command(name="boards")
@click.option("--full", "-f", is_flag=True, help="Print more details")
def list_boards(full: bool):
    """List available boards"""
    boards = core.list_json("boards")
    echo("Available boards:")
    for board_name in boards:
        board = core.get_board(board_name)
        echo(f" - '{board_name}': {board.name} / {board.vendor}")
        if full:
            echo(f"    - CPU: {board.build.mcu.upper()} @ {board.cpu_freq}")
            echo(f"    - Flash: {board.size_flash}")
            echo(f"    - RAM: {board.size_ram}")
            echo(f"    - Pin count: {len(board.pcb.pinout)}")
            echo(f"    - Connectivity: {board.connectivity}")


@list_cmd.command(name="templates")
@click.option("--full", "-f", is_flag=True, help="Print more details")
def list_templates(full: bool):
    """List available templates"""
    templates = core.list_json("templates")
    echo("Available templates:")
    for template_name in templates:
        template = Template(**core.load_template(template_name))
        echo(f" - '{template_name}': {template.title}")
        if full:
            echo(f"    - Size: {template.width} x {template.height} mm")
            echo(f"    - Pad count: {len(template.pads)}")


@list_cmd.command(name="shapes")
def list_shapes():
    """List available shapes"""
    templates = core.list_json("shapes")
    echo("Available shapes:")
    for shape_name in templates:
        echo(f" - '{shape_name}'")


@list_cmd.command(name="presets")
def list_presets():
    """List available presets"""
    echo("Available presets:")
    for preset_name, preset in core.presets.items():
        echo(f" - '{preset_name}'")


@list_cmd.command(name="roles")
def list_roles():
    """List available pin roles"""
    echo("Available pin roles:")
    for role_type, role in core.roles.items():
        echo(f" - {role_type.name}: {role.title}")


@list_cmd.command(name="flash")
def list_flash():
    """List available flash regions"""
    echo("Available flash regions:")
    for region_name, description in core.flash.items():
        echo(f" - {region_name}: {description}")
