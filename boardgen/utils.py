# Copyright (c) Kuba Szczodrzyński 2022-05-09.

import json
import re

from pydantic import BaseModel

from .vector import V

if_re = r"<(.+?):(.+?):(.+?):(.+?)>"


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
            raise ValueError(f"Missing variables: {s}")
        s_prev = s
    for match in re.findall(if_re, s):
        (var1, var2, true, false) = match
        full = f"<{var1}:{var2}:{true}:{false}>"
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


def merge_dicts(d1, d2):
    if d1 is not None and type(d1) != type(d2):
        raise TypeError(f"d1 and d2 are different types: {d1}, {d2}")
    if isinstance(d2, list):
        if d1 is None:
            d1 = []
        d1.extend(merge_dicts(None, item) for item in d2)
    elif isinstance(d2, dict):
        if d1 is None:
            d1 = {}
        for key in d2:
            d1[key] = merge_dicts(d1.get(key, None), d2[key])
    else:
        d1 = d2
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
