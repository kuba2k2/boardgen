# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from abc import ABC

from ..models import Role, RoleType
from ..utils import load_json


class CoreGetters(ABC):
    @property
    def presets(self) -> dict[str, dict]:
        if not self._presets:
            self._presets = load_json(self._file_presets)
        return self._presets

    @property
    def roles(self) -> dict[RoleType, Role]:
        if not self._roles:
            roles = load_json(self._file_roles)
            self._roles = {
                RoleType(key): Role(role_type=RoleType(key), **value)
                for key, value in roles.items()
            }
        return self._roles

    def role(self, role_type: RoleType) -> Role | None:
        return self.roles.get(role_type, None)

    @property
    def flash(self) -> dict[str, str]:
        if not self._flash:
            self._flash = load_json(self._file_flash)
        return self._flash
