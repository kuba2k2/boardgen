# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from abc import ABC
from glob import glob
from os.path import basename, isfile, join

from ..utils import load_json, merge_dicts


class CoreCache(ABC):
    _cache: dict[str, dict[str, dict]] = {
        "boards": {},
        "shapes": {},
        "templates": {},
    }

    def get_dirs(self, type: str) -> list[str]:
        attr_name = f"_dirs_{type}"
        if not hasattr(self, attr_name):
            return []
        return getattr(self, attr_name)

    def list_json(self, type: str) -> set[str]:
        dirs = self.get_dirs(type)
        files = set()
        for dir in dirs:
            for file in glob(join(dir, "*.json")):
                files.add(basename(file).rpartition(".")[0])
        return files

    def load_json(self, type: str, name: str) -> dict | None:
        if name in self._cache[type]:
            return self._cache[type][name]
        dirs = self.get_dirs(type)
        for dir in dirs:
            file = join(dir, f"{name}.json")
            if isfile(file):
                data = load_json(file)
                self._cache[type][name] = data
                return data
        return None

    def load_shape(self, name: str) -> dict:
        return self.load_json("shapes", name)

    def load_board_base(self, name: str) -> dict:
        name = join("_base", name)
        return self.load_json("boards", name)

    def load_board(self, name: str) -> dict:
        if name in self._cache["boards"]:
            return self._cache["boards"][name]
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
        self._cache["boards"][name] = manifest
        return manifest

    def load_template(self, name: str) -> dict:
        return self.load_json("templates", name)
