# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from abc import ABC
from glob import glob
from os.path import isfile, join, relpath
from typing import Callable, Optional

from ..utils import load_json, merge_dicts


class CoreCache(ABC):
    _cache: dict[str, dict[str, dict]] = {
        "boards": {},
        "board_objs": {},
        "shapes": {},
        "templates": {},
    }
    json_hook: Optional[Callable[[str, str, dict, Optional[str]], None]] = None

    def clear_cache(self) -> None:
        for obj in self._cache.values():
            obj.clear()
        self._presets = None
        self._roles = None
        self._flash = None

    def remove_from_cache(self, type: str, name: str) -> None:
        self._cache[type].pop(name, None)

    def get_dirs(self, type: str) -> list[str]:
        attr_name = f"_dirs_{type}"
        if not hasattr(self, attr_name):
            return []
        return getattr(self, attr_name)

    def list_json(self, type: str, recursive: bool = False) -> set[str]:
        dirs = self.get_dirs(type)
        files = set()
        for dir in dirs:
            for file in glob(
                join(dir, "**/*.json" if recursive else "*.json"),
                recursive=recursive,
            ):
                files.add(relpath(file, dir).replace("\\", "/").rpartition(".")[0])
        return files

    def load_json(self, type: str, name: str) -> dict | None:
        if name in self._cache[type]:
            if self.json_hook:
                self.json_hook(type, name, self._cache[type][name], None)
            return self._cache[type][name]
        dirs = self.get_dirs(type)
        for dir in dirs:
            file = join(dir, f"{name}.json")
            if isfile(file):
                data = load_json(file)
                self._cache[type][name] = data
                if self.json_hook:
                    self.json_hook(type, name, data, file)
                return data
        return None

    def load_shape(self, name: str) -> dict:
        return self.load_json("shapes", name)

    def load_board_base(self, name: str) -> dict:
        name = join("_base", name)
        return self.load_json("boards", name)

    def load_board(self, name: str, allow_cache: bool = True) -> dict:
        if allow_cache and name in self._cache["board_objs"]:
            return self._cache["board_objs"][name]
        manifest = self.load_json("boards", name)
        if "_base" in manifest:
            bases = manifest["_base"]
            if not isinstance(bases, list):
                bases = [bases]

            result = {}
            for base in bases:
                base_manifest = self.load_board_base(base)
                merge_dicts(result, base_manifest)
            merge_dicts(result, manifest)
            manifest = result
        self._cache["board_objs"][name] = manifest
        return manifest

    def load_template(self, name: str) -> dict:
        return self.load_json("templates", name)
