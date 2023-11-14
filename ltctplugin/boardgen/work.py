#  Copyright (c) Kuba Szczodrzyński 2023-11-14.

import sys
from logging import info
from pathlib import Path

from ltchiptool.gui.work.base import BaseThread
from ltchiptool.util.cli import run_subprocess
from ltchiptool.util.lvm import LVM, LVMPlatform


class LtciThread(BaseThread):
    def run_impl(self):
        lvm = LVM.get()
        platform = lvm.default()
        if not platform or platform.type not in [
            LVMPlatform.Type.PLATFORMIO,
            LVMPlatform.Type.CWD,
        ]:
            raise ValueError(
                "LibreTiny platform not found! "
                "Please install via PlatformIO or "
                "run ltchiptool in the LibreTiny directory"
            )

        info(f"Executing 'docs/scripts/write_boards.py' in {platform.path}")
        if run_subprocess(
            sys.executable,
            Path(platform.path).joinpath("docs/scripts/write_boards.py"),
            cwd=platform.path,
        ):
            return

        info(f"Executing 'boardgen ltci' in {platform.path}")
        if run_subprocess(
            sys.executable,
            "-m",
            "boardgen",
            "ltci",
            cwd=platform.path,
        ):
            return
