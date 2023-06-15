#  Copyright (c) Kuba Szczodrzyński 2023-5-20.

from typing import Any, Dict

from ltctplugin.base import PluginBase


class Plugin(PluginBase):
    @property
    def title(self) -> str:
        return "boardgen"

    @property
    def has_gui(self) -> bool:
        return True

    def build_gui(self, *args, **kwargs) -> Dict[str, Any]:
        from .gui import BoardgenPanel

        return dict(
            boardgen=BoardgenPanel,
        )


entrypoint = Plugin

__all__ = [
    "entrypoint",
]
