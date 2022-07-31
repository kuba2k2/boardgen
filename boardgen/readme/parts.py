# Copyright (c) Kuba Szczodrzyński 2022-05-14.

from abc import ABC


class ReadmeParts(ABC):
    items: list[str]

    def pad(self, s: str, i: int) -> str:
        return s + " " * (i - len(s))

    def add_heading(self, text: str, level: int = 1) -> "ReadmeParts":
        self.items.append(level * "#" + " " + text)
        return self

    def get_link(self, text: str, href: str) -> str:
        return f"[{text}]({href})"

    def get_img(self, alt: str, src: str) -> str:
        return f"![{alt}]({src})"

    def add_link(self, text: str, href: str) -> "ReadmeParts":
        self.items.append(self.get_link(text, href))
        return self

    def add_img(self, alt: str, src: str) -> "ReadmeParts":
        self.items.append(self.get_img(alt, src))
        return self

    def add_text(self, *text: str) -> "ReadmeParts":
        self.items.append(" ".join(text))
        return self

    def add_styled(self, style: str, *text: str) -> "ReadmeParts":
        self.items.append(style + " ".join(text) + style)
        return self

    def add_list(self, *items: list[str]) -> "ReadmeParts":
        items = [" ".join(i) for i in items]
        self.items.append("- " + "\n- ".join(items))
        return self

    def add_code(self, code: str | list[str], lang: str = None) -> "ReadmeParts":
        if isinstance(code, list):
            code = "\n".join(code)
        if not lang:
            lang = ""
        self.items.append(f"```{lang}\n{code}\n```")

    def add_table(self, header: list[str], *rows: list[str]) -> "ReadmeParts":
        maxlen = [len(h) for h in header]
        for row in rows:
            for i, col in enumerate(row):
                maxlen[i] = max(maxlen[i], len(col))
        lines = []
        header = [self.pad(h, maxlen[i]) for i, h in enumerate(header)]
        line = " | ".join(header)
        lines.append(line.rstrip())
        underline = ["-" * i for i in maxlen]
        line = "-|-".join(underline)
        lines.append(line.rstrip())
        for row in rows:
            row = [self.pad(h, maxlen[i]) for i, h in enumerate(row)]
            line = " | ".join(row)
            lines.append(line.rstrip())
        self.items.append("\n".join(lines))
        return self
