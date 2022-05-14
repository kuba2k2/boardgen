# Copyright (c) Kuba Szczodrzyński 2022-05-12.

from typing import Any

from pydantic import BaseModel, Field


class HasVars(BaseModel):
    vars: dict = {}

    def var(self, name: str) -> str | None:
        return self.vars.get(name, None)


class HasId(BaseModel):
    id: str = Field(None, alias="id")
    name: str = Field(None, alias="name")

    id_suffix: str = None

    @property
    def fullid(self) -> str | None:
        suffix = "." + self.id_suffix if self.id_suffix else ""
        if self.id:
            return self.id + suffix
        if self.name:
            return self.name + suffix
        if isinstance(self, HasVars) and "NAME" in self.vars:
            return self.var("NAME") + suffix
        return None


ParentType = HasVars | HasId | Any
