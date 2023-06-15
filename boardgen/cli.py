# Copyright (c) Kuba Szczodrzyński 2022-05-09.

import os
from os.path import isfile, join

import click
from click import echo
from devtools import debug

from . import Core
from .draw_util import draw_shapes, get_pcb_images
from .models import Board, Template
from .readme.writer import ReadmeWriter
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
    default=None,
    type=float,
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

    scale_arg = scale

    for board in boards:
        board: Board
        if not board.pcb or not board.pcb.templates:
            echo(f"Skipping '{board.name}'...")
            continue
        echo(f"Drawing '{board.name}'...")

        pcb = board.pcb

        if scale_arg is None:
            scale = pcb.scale or 12
        else:
            scale = scale_arg

        images = get_pcb_images(core, pcb, labels)
        dwg = draw_shapes(px_size, scale, images, canvas)

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
        out_c = join(output, f"{board.id}.c")
        if subdir:
            out_h = join(output, board.id, f"variant.h")
            out_c = join(output, board.id, f"variant.c")

        echo(f"Saving to '{out_h}' and '{out_c}'...")
        board_name = f"{board.id}.json"
        writer.save_h(out_h, board_name)
        if writer.pins:
            writer.save_c(out_c, board_name)


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


@cli.command()
@click.option("--no-docs", "-D", is_flag=True, help="Write variant files only")
@click.pass_context
def ltci(ctx, no_docs: bool):
    """Generate board files for LibreTiny CI"""
    if not isfile("families.json"):
        print("Run this command in LT root directory")
        exit(1)
    boards = load_boards(["all"])

    if not no_docs:
        ctx.invoke(draw, boards=boards, output="boards/", subdir=True)
        ctx.invoke(write, boards=boards, output="boards/", subdir=True)
    ctx.invoke(variant, boards=boards, output="boards/variants/", subdir=False)


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


if __name__ == "__main__":
    cli()
