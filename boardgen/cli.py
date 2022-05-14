# Copyright (c) Kuba Szczodrzyński 2022-05-09.

import os
from os.path import join

import click
from click import echo
from click.core import Context
from devtools import debug
from svgwrite import Drawing, shapes

from . import Core
from .models import Board, Side, Template
from .shapes.label import Label
from .utils import load_json
from .vector import V

core = Core()


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
    boards: str,
    dump: bool,
    output: str,
    width: int,
    height: int,
    scale: float,
    canvas: bool,
    labels: bool,
):
    """Draw board diagrams"""
    boards = [
        echo(f"Loading board '{board}'...") or core.get_board(board) for board in boards
    ]
    if dump:
        for board in boards:
            debug(board)
        ctx.exit()

    px_size = V(width, height)

    if output:
        os.makedirs(output, exist_ok=True)

    for board in boards:
        board: Board
        echo(f"Drawing '{board.name}'...")

        pcb = board.pcb
        (pcb_pos1, pcb_pos2) = pcb.get_pos(Side.FRONT)
        pcb_size = pcb_pos2 - pcb_pos1
        if labels:
            (labels_list, labels_pos1, labels_pos2) = core.build_labels(pcb)
            # labels_size = labels_pos2 - labels_pos1

        if scale:
            vb_size = px_size / scale
        else:
            size_pad = px_size * 0.90  # 5% padding from each side
            if labels:
                pos1 = V(min(pcb_pos1.x, labels_pos1.x), min(pcb_pos1.y, labels_pos1.y))
                pos2 = V(max(pcb_pos2.x, labels_pos2.x), max(pcb_pos2.y, labels_pos2.y))
                size = pos2 - pos1
            else:
                size = pcb_size
            scale_auto = min(size_pad.x / size.x, size_pad.y / size.y)
            echo(" - calculated scale: %.2f" % scale_auto)
            vb_size = px_size / scale_auto

        pcb_pos = (vb_size - pcb_size) / 2

        dwg = Drawing(size=px_size.tuple)
        dwg.viewbox(width=vb_size.x, height=vb_size.y)

        if canvas:
            bg = shapes.Rect(insert=(0, 0), size=vb_size.tuple)
            bg.fill(color="white")
            bg.stroke(color="black", width=0.1)
            dwg.add(bg)

        pcb.draw(dwg, Side.FRONT, pcb_pos)
        if labels:
            for label in labels_list:
                label: Label
                label.move(pcb_pos)
                label.draw(dwg)
                label.move(-pcb_pos)

        with open(
            join(output, f"{board.build.variant}.svg"), "w", encoding="utf-8"
        ) as f:
            dwg.write(f, pretty=True, indent=4)


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
