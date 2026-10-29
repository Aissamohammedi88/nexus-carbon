#!/usr/bin/env python3
"""NEXUS-COBOL lexer (v1.1 NOBLE) — stdlib only, protocole ULTRA.

Format libre : commentaires `*>` jusqu'à la fin de ligne, chaînes entre
guillemets doubles sur une seule ligne, identifiants avec tirets
(style COBOL : COMPTEUR-2 est UN nom).

Un token = (kind, value, line, first_on_line)
    kind ∈ {STR, NUM, IDENT, SYM}
    first_on_line sert au parser pour reconnaître les paragraphes
    (un paragraphe = identificateur en tête de ligne suivi d'un point).
"""

from __future__ import annotations

import re
from typing import List, Tuple

Token = Tuple[str, object, int, bool]

_TOKEN_RE = re.compile(
    r"""
      (?P<WS>\s+)
    | (?P<COMMENT>\*>[^\n]*)
    | (?P<STR>"[^"\n]*")
    | (?P<NUM>\d+\.\d+|\d+)
    | (?P<IDENT>[A-Za-z][A-Za-z0-9-]*)
    | (?P<SYM>\*\*|<=|>=|<>|!=|[=<>+\-*/().,])
    """,
    re.VERBOSE,
)


def lex_text(text: str) -> List[Token]:
    tokens: List[Token] = []
    line = 1
    first = True
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN_RE.match(text, pos)
        if m is None:
            raise SyntaxError(f"caractère illégal {text[pos]!r} à la ligne {line}")
        kind = m.lastgroup
        raw = m.group()
        if kind == "WS":
            nl = raw.count("\n")
            if nl:
                line += nl
                first = True
            pos = m.end()
            continue
        if kind == "COMMENT":
            pos = m.end()
            continue
        if kind == "STR":
            value: object = raw[1:-1]
        elif kind == "NUM":
            value = float(raw) if "." in raw else int(raw)
        else:
            value = raw
        tokens.append((kind, value, line, first))
        first = False
        pos = m.end()
    return tokens


def lex_file(path: str) -> List[Token]:
    with open(path, "r", encoding="utf-8") as fh:
        return lex_text(fh.read())


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: nexus_cobol_lexer.py <file.nxc>", file=sys.stderr)
        sys.exit(2)
    toks = lex_file(sys.argv[1])
    print(f"tokens={len(toks)}")
