#  Copyright (c) Kuba Szczodrzyński 2023-6-3.

import json

from ltchiptool.util.dict import get

MARKER = "\ufffc"
LF = "\n"


def find_marker(obj: dict | list) -> str | None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if MARKER in key:
                return key.replace(MARKER, "")
            if isinstance(value, (dict, list)):
                ret = find_marker(value)
                if ret:
                    return f"{key}.{ret}"
            if isinstance(value, str) and MARKER in value:
                return key
    elif isinstance(obj, list):
        for key, value in enumerate(obj):
            if isinstance(value, (dict, list)):
                ret = find_marker(value)
                if ret:
                    return f"{key}.{ret}"
            if isinstance(value, str) and MARKER in value:
                return str(key)
    return None


def jsonpath(s: str, p: int) -> str | None:
    before = s[0:p]
    after = s[p:]
    if (
        before.endswith("\\")
        and after.startswith("\\")
        and not before.endswith("\\\\")
        and not after.startswith("\\\\")
    ):
        p -= 1
        before = s[0:p]
        after = s[p:]
    try:
        # try deserializing with added marker
        s = before + MARKER + after
        # print(s)
        obj = json.loads(s)
        return find_marker(obj)
    except json.JSONDecodeError:
        pass

    before, _, line_start = before.rpartition(LF)
    line_end, _, after = after.partition(LF)
    try:
        dist_start = len(line_start) - line_start.rindex('"')
    except ValueError:
        dist_start = len(s)
    try:
        dist_end = line_end.index('"') + 1
    except ValueError:
        dist_end = len(s)
    if dist_start <= dist_end:
        s = (
            before
            + LF
            + line_start[:-dist_start]
            + MARKER
            + line_start[-dist_start:]
            + line_end
            + LF
            + after
        )
    elif dist_end < dist_start:
        s = (
            before
            + LF
            + line_start
            + line_end[:dist_end]
            + MARKER
            + line_end[dist_end:]
            + LF
            + after
        )
    try:
        # print(s)
        obj = json.loads(s)
        return find_marker(obj)
    except json.JSONDecodeError:
        pass

    before = before + LF + line_start
    after = line_end + LF + after
    try:
        dist_before = len(before) - before.rindex('"')
    except ValueError:
        dist_before = len(s)
    try:
        dist_after = after.index('"') + 1
    except ValueError:
        dist_after = len(s)
    if dist_before <= dist_after:
        s = before[:-dist_before] + MARKER + before[-dist_before:] + after
    elif dist_after < dist_before:
        s = before + after[:dist_after] + MARKER + after[dist_after:]
    try:
        # print(s)
        obj = json.loads(s)
        return find_marker(obj)
    except json.JSONDecodeError:
        pass
    return None


def jsonwalk(obj: dict | list, path: str) -> tuple[dict | list, str | int] | None:
    while "." in path:
        key, _, path = path.partition(".")
        if isinstance(obj, list) and key.isnumeric():
            obj = obj[int(key)]
        elif isinstance(obj, dict):
            obj = obj[key]
        else:
            return None
    if isinstance(obj, list) and path.isnumeric():
        path = int(path)
    elif not isinstance(obj, dict):
        return None
    return obj, path


def test_jsonpath():
    json_data = """
    {
        "mask_black": {
            "fill": {
                "lgrad": ["1,0", "#4D4D4D", "0,1", "#0F0F0F"]
            },
            "stroke": {
                "color": "#B5A739",
                "width": 0.1
            }
        }
    }
    """

    obj = json.loads(json_data)
    for i in range(0, len(json_data)):
        path = jsonpath(json_data, i)
        value = get(obj, path)
        print(f"{i=}", obj, path, value)


if __name__ == "__main__":
    test_jsonpath()
