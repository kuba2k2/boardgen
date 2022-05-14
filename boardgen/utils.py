# Copyright (c) Kuba Szczodrzyński 2022-05-09.

import json
import re

from pydantic import BaseModel

from .vector import V

if_re = r"\((.+?):(.+?):(.+?):(.+?)\)"


class Model(BaseModel):
    class Config:
        arbitrary_types_allowed = True


def var(s: str, vars: dict) -> str:
    s_prev = s
    while "${" in s:
        for key, value in vars.items():
            s = s.replace(f"${{{key}}}", str(value))
        if s == s_prev:
            # no replacements made anymore
            break
    for match in re.findall(if_re, s):
        (var1, var2, true, false) = match
        full = f"({var1}:{var2}:{true}:{false})"
        result = true if var1.strip() == var2.strip() else false
        s = s.replace(full, result)
    return s


def str_to_num(s: str) -> float:
    s = s.strip()
    s = eval(s)
    return float(s)


def splitxy(xy: str | tuple | V) -> V:
    if isinstance(xy, tuple):
        return V(xy)
    if isinstance(xy, V):
        return V(xy)
    return V(tuple(map(str_to_num, xy.split(","))))


def merge_dicts(d1, d2, path=None):
    if path is None:
        path = []
    for key in d2:
        if key in d1 and isinstance(d1[key], dict) and isinstance(d2[key], dict):
            merge_dicts(d1[key], d2[key], path + [str(key)])
        else:
            d1[key] = d2[key]
    return d1


def load_json(file: str) -> dict | list:
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


# https://stackoverflow.com/a/1094933/9438331
def sizeof(num: int, suffix="iB", base=1024.0) -> str:
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < base:
            return f"{num:.1f} {unit}{suffix}".replace(".0 ", " ")
        num /= base
    return f"{num:.1f} Y{suffix}".replace(".0 ", " ")
