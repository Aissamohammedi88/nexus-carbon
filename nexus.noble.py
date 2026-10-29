#!/usr/bin/env python3
"""NEXUS-COBOL parser (v1.1 NOBLE) — grammaire du Language Systémique DGK.

Verbes COBOL classiques :
    DISPLAY, MOVE, COMPUTE, ADD, SUBTRACT, MULTIPLY, DIVIDE,
    IF/THEN/ELSE/END-IF, EVALUATE/WHEN/OTHER/END-EVALUATE,
    PERFORM (paragraphe, n TIMES, UNTIL, VARYING — hors-ligne et inline),
    STOP RUN.   DATA DIVISION : niveau, PIC 9(n)/X(n), VALUE.

Verbes systémiques (l'option noble : le langage invoque les pouvoirs
GPTNexus directement depuis le programme) :
    SCAN-FILE <path> [REPORTING <path>]
    PROBE-FILE <file> RULE <rule>
    PATCH-FILE <file> [RULE <rule>]
    SWEEP-PATH <path>
    REMEMBER <key> VALUE <atom>          / RECALL <key> [INTO <var>] [DISPLAY]
    ASK-GLM <question>
    CONTEXT-LOAD FILE <path> [LIMIT <n>] / CONTEXT-SEARCH <query>
    NOTE-METRIC <name> VALUE <expr>

Sémantique v1.1 :
  - DISPLAY concatène SANS séparateur (COBOL authentique).
  - un paragraphe = identificateur en TÊTE de ligne suivi d'un point.
  - END-IF / END-EVALUATE / END-PERFORM obligatoires.
  - PERFORM hors-ligne (avec nom de paragraphe) se termine par un point ;
    PERFORM inline (corps d'énoncés) se termine par END-PERFORM.
  - AND / OR même précédence, associativité gauche, pas de parenthèses
    dans les conditions (documenté).
"""
from __future__ import annotations

from nexus_cobol_lexer import lex_file, lex_text

KEYWORDS = {
    "IDENTIFICATION", "DATA", "PROCEDURE", "DIVISION", "SECTION",
    "WORKING-STORAGE", "PROGRAM-ID", "AUTHOR", "PIC", "VALUE",
    "DISPLAY", "MOVE", "COMPUTE", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE",
    "TO", "FROM", "BY", "GIVING", "INTO",
    "IF", "THEN", "ELSE", "END-IF", "EVALUATE", "WHEN", "OTHER", "END-EVALUATE",
    "PERFORM", "END-PERFORM", "UNTIL", "VARYING", "TIMES",
    "STOP", "RUN", "AND", "OR",
    "SCAN-FILE", "REPORTING", "PROBE-FILE", "RULE", "PATCH-FILE", "SWEEP-PATH",
    "REMEMBER", "RECALL", "ASK-GLM",
    "CONTEXT-LOAD", "FILE", "LIMIT", "CONTEXT-SEARCH", "NOTE-METRIC",
    "ZERO", "ZEROS", "SPACE", "SPACES",
}

RELOPS = {"=", "<>", "!=", ">", "<", ">=", "<="}


class NexusSyntaxError(SyntaxError):
    pass


class Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    # ------------------------------------------------------------- helpers
    def peek(self, k=0):
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else ("EOF", None, -1, False)

    def advance(self):
        tok = self.peek()
        self.i += 1
        return tok

    def kw(self, word, k=0):
        kind, val, _, _ = self.peek(k)
        return kind == "IDENT" and str(val).upper() == word

    def take_kw(self, word):
        return self.advance() if self.kw(word) else None

    def expect_kw(self, word):
        if not self.take_kw(word):
            raise NexusSyntaxError(
                f"attendu {word}, trouvé {self.peek()[1]!r} (ligne {self.peek()[2]})"
            )

    def peek_sym(self, s, k=0):
        kind, val, _, _ = self.peek(k)
        return kind == "SYM" and val == s

    def take_sym(self, s):
        return self.advance() if self.peek_sym(s) else None

    def expect_sym(self, s):
        if not self.take_sym(s):
            raise NexusSyntaxError(
                f"attendu {s!r}, trouvé {self.peek()[1]!r} (ligne {self.peek()[2]})"
            )

    def skip_periods(self):
        while self.peek_sym("."):
            self.advance()

    # ------------------------------------------------------------- program
    def parse_program(self) -> dict:
        program_id = "ANONYME"
        author = ""
        data: dict = {}
        paragraphs: list = []

        # identification division (optionnelle pour un mini-programme)
        if self.kw("IDENTIFICATION"):
            self.expect_kw("IDENTIFICATION")
            self.expect_kw("DIVISION")
            self.skip_periods()
            if self.kw("PROGRAM-ID"):
                self.advance()
                self.skip_periods()  # le point suit immédiatement PROGRAM-ID
                kind, val, _, _ = self.peek()
                if kind == "IDENT":
                    program_id = str(val)
                    self.advance()
                self.skip_periods()
            if self.kw("AUTHOR"):
                self.advance()
                self.skip_periods()  # le point suit immédiatement AUTHOR
                parts: list = []
                while self.peek()[0] != "EOF" and not self.peek_sym("."):
                    parts.append(str(self.peek()[1]))
                    self.advance()
                author = " ".join(parts)
                self.take_sym(".")

        if self.kw("DATA"):
            self.expect_kw("DATA")
            self.expect_kw("DIVISION")
            self.skip_periods()
            if self.kw("WORKING-STORAGE"):
                self.advance()
                self.expect_kw("SECTION")
                self.skip_periods()
            data = self.parse_data_entries()

        if self.kw("PROCEDURE"):
            self.expect_kw("PROCEDURE")
            self.expect_kw("DIVISION")
            self.skip_periods()
            paragraphs = self.parse_paragraphs()

        if self.peek()[0] != "EOF":
            raise NexusSyntaxError(
                f"texte inattendu après le programme : {self.peek()[1]!r} "
                f"(ligne {self.peek()[2]})"
            )
        return {
            "program_id": program_id,
            "author": author,
            "data": data,
            "paragraphs": paragraphs,
        }

    # ------------------------------------------------------------- data
    def parse_data_entries(self) -> dict:
        entries: dict = {}
        while True:
            kind, val, _, _ = self.peek()
            if kind == "NUM" and isinstance(val, int) and 1 <= val <= 49:
                nxt = self.peek(1)
                if nxt[0] != "IDENT" or str(nxt[1]).upper() in KEYWORDS:
                    raise NexusSyntaxError(
                        f"nom de donnée manquant après le niveau {val} "
                        f"(ligne {self.peek()[2]})"
                    )
                self.advance()  # niveau
                name = str(self.advance()[1]).upper()
                meta = {"numeric": True, "size": 9, "init": 0}
                if self.kw("PIC"):
                    self.advance()
                    pkind, pval, _, _ = self.peek()
                    if pkind == "NUM" and pval == 9:
                        self.advance()
                        meta["numeric"] = True
                    elif pkind == "IDENT" and str(pval).upper() in ("X", "A"):
                        self.advance()
                        meta["numeric"] = False
                        meta["init"] = ""
                    else:
                        raise NexusSyntaxError(
                            f"PIC supporté : 9(n) ou X(n) — trouvé {pval!r} "
                            f"(ligne {self.peek()[2]})"
                        )
                    if self.peek_sym("("):
                        self.advance()
                        skind, sval, _, _ = self.peek()
                        if skind != "NUM" or not isinstance(sval, int):
                            raise NexusSyntaxError(
                                f"taille PIC numérique attendue (ligne {self.peek()[2]})"
                            )
                        meta["size"] = sval
                        self.advance()
                        self.expect_sym(")")
                    else:
                        meta["size"] = 1
                if self.kw("VALUE"):
                    self.advance()
                    meta["init"] = self.parse_literal()
                self.skip_periods()
                entries[name] = meta
            else:
                break
        return entries

    def parse_literal(self):
        kind, val, _, _ = self.peek()
        if kind == "STR" or kind == "NUM":
            self.advance()
            return val
        if kind == "IDENT" and str(val).upper() in ("ZERO", "ZEROS"):
            self.advance()
            return 0
        if kind == "IDENT" and str(val).upper() in ("SPACE", "SPACES"):
            self.advance()
            return ""
        raise NexusSyntaxError(
            f"littéral attendu après VALUE — trouvé {val!r} (ligne {self.peek()[2]})"
        )

    # ------------------------------------------------------------- paragraphs
    def parse_paragraphs(self) -> list:
        paragraphs: list = []
        current: list = []
        name = "MAIN"
        started = False
        self.skip_periods()
        while self.peek()[0] != "EOF":
            kind, val, line, first = self.peek()
            nxt = self.peek(1)
            if (
                kind == "IDENT"
                and first
                and str(val).upper() not in KEYWORDS
                and nxt[0] == "SYM"
                and nxt[1] == "."
            ):
                if started:
                    paragraphs.append((name, current))
                name = str(val).upper()
                self.advance()
                self.advance()  # point
                current = []
                started = True
                self.skip_periods()
                continue
            current.append(self.parse_statement())
            self.skip_periods()
        if started:
            paragraphs.append((name, current))
        return paragraphs

    # ------------------------------------------------------------- blocks
    def parse_block(self, stop: set) -> list:
        stmts: list = []
        while True:
            kind, val, _, _ = self.peek()
            if kind == "EOF":
                break
            if kind == "IDENT" and str(val).upper() in stop:
                break
            stmts.append(self.parse_statement())
            self.skip_periods()
        return stmts

    # ------------------------------------------------------------- statements
    def parse_statement(self):
        kind, val, line, _ = self.peek()
        if kind != "IDENT":
            raise NexusSyntaxError(f"énoncé attendu, trouvé {val!r} (ligne {line})")
        verb = str(val).upper()
        if verb == "DISPLAY":
            return self.p_display()
        if verb == "MOVE":
            return self.p_move()
        if verb == "COMPUTE":
            return self.p_compute()
        if verb == "ADD":
            return self.p_arith("ADD")
        if verb == "SUBTRACT":
            return self.p_arith("SUBTRACT")
        if verb == "MULTIPLY":
            return self.p_arith("MULTIPLY")
        if verb == "DIVIDE":
            return self.p_divide()
        if verb == "IF":
            return self.p_if()
        if verb == "EVALUATE":
            return self.p_evaluate()
        if verb == "PERFORM":
            return self.p_perform()
        if verb == "STOP":
            self.advance()
            self.expect_kw("RUN")
            return ("STOP",)
        if verb == "SCAN-FILE":
            self.advance()
            path = self.parse_atom()
            reporting = None
            if self.take_kw("REPORTING"):
                reporting = self.parse_atom()
            return ("SCAN-FILE", path, reporting)
        if verb == "PROBE-FILE":
            self.advance()
            file_a = self.parse_atom()
            self.expect_kw("RULE")
            rule_a = self.parse_atom()
            return ("PROBE-FILE", file_a, rule_a)
        if verb == "PATCH-FILE":
            self.advance()
            file_a = self.parse_atom()
            rule_a = None
            if self.take_kw("RULE"):
                rule_a = self.parse_atom()
            return ("PATCH-FILE", file_a, rule_a)
        if verb == "SWEEP-PATH":
            self.advance()
            return ("SWEEP-PATH", self.parse_atom())
        if verb == "REMEMBER":
            self.advance()
            key = self.parse_atom()
            self.expect_kw("VALUE")
            return ("REMEMBER", key, self.parse_atom())
        if verb == "RECALL":
            self.advance()
            key = self.parse_atom()
            into = None
            show = False
            if self.take_kw("INTO"):
                into = self.expect_ident("variable cible")
            if self.take_kw("DISPLAY"):
                show = True
            return ("RECALL", key, into, show)
        if verb == "ASK-GLM":
            self.advance()
            return ("ASK-GLM", self.parse_atom())
        if verb == "CONTEXT-LOAD":
            self.advance()
            self.expect_kw("FILE")
            path = self.parse_atom()
            limit = None
            if self.take_kw("LIMIT"):
                lkind, lval, _, _ = self.peek()
                if lkind != "NUM" or not isinstance(lval, int):
                    raise NexusSyntaxError("LIMIT attend un entier")
                limit = lval
                self.advance()
            return ("CONTEXT-LOAD", path, limit)
        if verb == "CONTEXT-SEARCH":
            self.advance()
            return ("CONTEXT-SEARCH", self.parse_atom())
        if verb == "NOTE-METRIC":
            self.advance()
            name_a = self.parse_atom()
            self.expect_kw("VALUE")
            return ("NOTE-METRIC", name_a, self.parse_expr())
        raise NexusSyntaxError(
            f"verbe inconnu {verb} (ligne {line}) — voir docs/AUDIT.md pour la liste"
        )

    def expect_ident(self, what: str) -> str:
        kind, val, line, _ = self.peek()
        if kind != "IDENT" or str(val).upper() in KEYWORDS:
            raise NexusSyntaxError(f"{what} attendu (ligne {line})")
        self.advance()
        return str(val).upper()

    def p_display(self):
        self.advance()
        items: list = []
        while True:
            kind, val, _, _ = self.peek()
            if kind in ("STR", "NUM"):
                items.append(("lit", val))
                self.advance()
            elif kind == "IDENT" and str(val).upper() not in KEYWORDS:
                items.append(("var", str(val).upper()))
                self.advance()
            else:
                break
        if not items:
            raise NexusSyntaxError(
                f"DISPLAY sans élément (ligne {self.peek()[2]})"
            )
        return ("DISPLAY", items)

    def p_move(self):
        self.advance()
        src = self.parse_atom()
        self.expect_kw("TO")
        targets = [self.expect_ident("cible MOVE")]
        while self.peek()[0] == "IDENT" and str(self.peek()[1]).upper() not in KEYWORDS:
            targets.append(str(self.advance()[1]).upper())
        return ("MOVE", src, targets)

    def p_compute(self):
        self.advance()
        target = self.expect_ident("cible COMPUTE")
        self.expect_sym("=")
        return ("COMPUTE", target, self.parse_expr())

    def p_arith(self, verb: str):
        self.advance()
        operand = self.parse_expr()
        if verb == "ADD":
            self.expect_kw("TO")
        elif verb == "SUBTRACT":
            self.expect_kw("FROM")
        else:
            self.expect_kw("BY")
        target = self.expect_ident("cible arithmétique")
        giving = None
        if self.take_kw("GIVING"):
            giving = self.expect_ident("cible GIVING")
        return (verb, operand, target, giving)

    def p_divide(self):
        self.advance()
        a = self.parse_expr()
        if self.take_kw("INTO"):
            target = self.expect_ident("cible DIVIDE INTO")
            giving = None
            if self.take_kw("GIVING"):
                giving = self.expect_ident("cible GIVING")
            return ("DIVIDE", "INTO", a, target, giving)
        self.expect_kw("BY")
        b = self.parse_expr()
        self.expect_kw("GIVING")
        giving = self.expect_ident("cible GIVING")
        return ("DIVIDE", "BY", a, b, giving)

    def p_if(self):
        self.advance()
        cond = self.parse_cond()
        self.take_kw("THEN")
        then_stmts = self.parse_block({"ELSE", "END-IF"})
        else_stmts: list = []
        if self.take_kw("ELSE"):
            else_stmts = self.parse_block({"END-IF"})
        self.expect_kw("END-IF")
        return ("IF", cond, then_stmts, else_stmts)

    def p_evaluate(self):
        self.advance()
        subject = self.parse_expr()
        branches: list = []
        other: list = []
        while self.kw("WHEN"):
            self.advance()
            if self.kw("OTHER"):
                self.advance()
                other = self.parse_block({"WHEN", "END-EVALUATE"})
                break
            values = [self.parse_atom()]
            while self.take_kw("OR"):
                values.append(self.parse_atom())
            stmts = self.parse_block({"WHEN", "END-EVALUATE"})
            branches.append((values, stmts))
        self.expect_kw("END-EVALUATE")
        return ("EVALUATE", subject, branches, other)

    def p_perform(self):
        self.advance()
        kind, val, _, _ = self.peek()
        # PERFORM UNTIL cond ... END-PERFORM            (inline)
        if self.kw("UNTIL"):
            self.advance()
            cond = self.parse_cond()
            if self.peek_sym("."):
                raise NexusSyntaxError(
                    "PERFORM UNTIL inline exige END-PERFORM "
                    "(ligne {self.peek()[2]})"
                )
            body = self.parse_block({"END-PERFORM"})
            self.expect_kw("END-PERFORM")
            return ("PERFORM", "inline_until", cond, body)
        # PERFORM VARYING v FROM x BY y UNTIL cond ...   (inline ou hors-ligne)
        if self.kw("VARYING"):
            self.advance()
            var = self.expect_ident("variable VARYING")
            self.expect_kw("FROM")
            frm = self.parse_expr()
            self.expect_kw("BY")
            by = self.parse_expr()
            self.expect_kw("UNTIL")
            cond = self.parse_cond()
            return self.p_perform_tail_varying(var, frm, by, cond)
        # PERFORM n TIMES ... END-PERFORM                (inline)
        if kind == "NUM":
            times = self.parse_atom()
            self.expect_kw("TIMES")
            body = self.parse_block({"END-PERFORM"})
            self.expect_kw("END-PERFORM")
            return ("PERFORM", "inline_times", times, body)
        # PERFORM <paragraphe> [clauses] [.]
        if kind == "IDENT" and str(val).upper() not in KEYWORDS:
            name = str(self.advance()[1]).upper()
            if self.kw("UNTIL"):
                self.advance()
                cond = self.parse_cond()
                return ("PERFORM", "para_until", name, cond)
            if self.peek()[0] == "NUM":
                times = self.parse_atom()
                self.expect_kw("TIMES")
                return ("PERFORM", "para_times", name, times)
            return ("PERFORM", "para", name)
        raise NexusSyntaxError(
            f"forme PERFORM non reconnue (ligne {self.peek()[2]})"
        )

    def p_perform_tail_varying(self, var, frm, by, cond):
        kind, val, _, _ = self.peek()
        if kind == "IDENT" and str(val).upper() not in KEYWORDS:
            nxt = self.peek(1)
            if nxt[0] == "SYM" and nxt[1] == ".":
                name = str(self.advance()[1]).upper()
                return ("PERFORM", "para_varying", name, var, frm, by, cond)
        body = self.parse_block({"END-PERFORM"})
        self.expect_kw("END-PERFORM")
        return ("PERFORM", "inline_varying", var, frm, by, cond, body)

    # ------------------------------------------------------------- atoms/expr/cond
    def parse_atom(self):
        kind, val, line, _ = self.peek()
        if kind in ("STR", "NUM"):
            self.advance()
            return ("lit", val)
        if kind == "IDENT":
            up = str(val).upper()
            if up in ("ZERO", "ZEROS"):
                self.advance()
                return ("lit", 0)
            if up in ("SPACE", "SPACES"):
                self.advance()
                return ("lit", "")
            if up not in KEYWORDS:
                self.advance()
                return ("var", up)
        raise NexusSyntaxError(f"atome attendu — trouvé {val!r} (ligne {line})")

    def parse_expr(self):
        node = self.parse_term()
        while self.peek_sym("+") or self.peek_sym("-"):
            op = self.advance()[1]
            node = ("bin", op, node, self.parse_term())
        return node

    def parse_term(self):
        node = self.parse_pow()
        while self.peek_sym("*") or self.peek_sym("/"):
            op = self.advance()[1]
            node = ("bin", op, node, self.parse_pow())
        return node

    def parse_pow(self):
        node = self.parse_factor()
        if self.peek_sym("**"):
            self.advance()
            node = ("bin", "**", node, self.parse_pow())
        return node

    def parse_factor(self):
        kind, val, line, _ = self.peek()
        if kind == "NUM" or kind == "STR":
            self.advance()
            return ("lit" if kind == "NUM" else "str", val)
        if kind == "IDENT" and str(val).upper() not in KEYWORDS:
            self.advance()
            return ("var", str(val).upper())
        if self.peek_sym("("):
            self.advance()
            node = self.parse_expr()
            self.expect_sym(")")
            return node
        if self.peek_sym("-"):
            self.advance()
            return ("neg", self.parse_factor())
        raise NexusSyntaxError(f"expression attendue — trouvé {val!r} (ligne {line})")

    def parse_cond(self):
        node = self.parse_comparison()
        while self.kw("AND") or self.kw("OR"):
            op = str(self.advance()[1]).upper()
            rhs = self.parse_comparison()
            node = ("and" if op == "AND" else "or", node, rhs)
        return node

    def parse_comparison(self):
        left = self.parse_expr()
        kind, val, line, _ = self.peek()
        if kind != "SYM" or val not in RELOPS:
            raise NexusSyntaxError(
                f"opérateur relationnel attendu (= <> != > < >= <=) — "
                f"trouvé {val!r} (ligne {line})"
            )
        self.advance()
        right = self.parse_expr()
        return ("cmp", val, left, right)


def parse_file(path: str) -> dict:
    return Parser(lex_file(path)).parse_program()


def parse_text(text: str) -> dict:
    return Parser(lex_text(text)).parse_program()
