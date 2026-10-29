NOBLE).

C'est LA fonctionnalité « plus noble que Gemini » demandée par DGK : un
vrai langage systémique façon COBOL dont les verbes invoquent directement
les pouvoirs de GPTNexus :

    COBOL classique     -> DISPLAY MOVE COMPUTE ADD SUBTRACT MULTIPLY
                           DIVIDE IF EVALUATE PERFORM STOP RUN
    Verbes systémiques  -> SCAN-FILE   (Scanner Rust, preuves JSON)
                           PROBE-FILE  (ExploitGym, sondes contrôlées)
                           PATCH-FILE  (Patcher, persistance + impasses)
                           SWEEP-PATH  (pipeline autonome complet)
                           REMEMBER/RECALL (mémoire persistante .nexus/)
                           ASK-GLM     (cerveau famille, avis [glm-advisory])
                           CONTEXT-LOAD/CONTEXT-SEARCH (mémoire 1M tokens)
                           NOTE-METRIC (registre de métriques)

Honnêteté ULTRA : c'est un interpréteur local réel, testé par le banc
(N14-N21). Ce n'est PAS un mainframe COBOL (pas de DBMS/CICS/JCL) et
ASK-GLM n'est pas une preuve — le label [glm-advisory] l'encadre.

Sécurité : budget d'instructions (défaut 200 000) — toute boucle infinie
est abortée avec exit 3 et le message BUDGET EXCEEDED. Test N21.

Usage :
    python3 nexus_cobol.py <file.nxc> [--max-steps N] [--json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import nexus_core
from nexus_cobol_lexer import lex_file
from nexus_cobol_parser import NexusSyntaxError, Parser

VERSION = "1.1"
DEFAULT_MAX_STEPS = 200_000
MAX_DEPTH = 100


class NexusRuntimeError(Exception):
    pass


class BudgetExceeded(NexusRuntimeError):
    pass


class StopRun(Exception):
    pass


def _fmt(value) -> str:
    """Affichage : 5.0 -> '5' (les flottants entiers s'affichent sans .0)."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class Machine:
    """Exécute un programme NEXUS-COBOL. Chaque verbe systémique est
    consigné au registre de mission (Ledger) — le programme COBOL EST
    une mission GPTNexus."""

    def __init__(self, max_steps: int = DEFAULT_MAX_STEPS):
        self.max_steps = max_steps
        self.steps = 0
        self.depth = 0
        self.vars: dict = {}
        self.data: dict = {}
        self.paras: dict = {}
        self.root = Path.cwd()
        self.nexus_dir = self.root / ".nexus"
        self.nexus_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = nexus_core.Ledger(self.root)
        self._scanner = None
        self._gym = None
        self._brain = None
        self._context = None

    # ------------------------------------------------------------ lazy tools
    def scanner(self):
        if self._scanner is None:
            self._scanner = nexus_core.Scanner()
        return self._scanner

    def gym(self):
        if self._gym is None:
            self._gym = nexus_core.ExploitGym()
        return self._gym

    def brain(self):
        if self._brain is None:
            self._brain = nexus_core.GLMBrain()
        return self._brain

    def context(self):
        if self._context is None:
            import nexus_context

            self._context = nexus_context.ContextEngine()
        return self._context

    # ------------------------------------------------------------ memory io
    def _load_json(self, path: Path, default):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return default

    def memory(self) -> dict:
        return self._load_json(self.nexus_dir / "cobol_memory.json", {})

    def metrics(self) -> dict:
        return self._load_json(self.nexus_dir / "metrics.json", {})

    # ------------------------------------------------------------ run
    def run(self, prog: dict) -> int:
        self.data = prog["data"]
        self.paras = {name: stmts for name, stmts in prog["paragraphs"]}
        for name, meta in self.data.items():
            self.vars[name] = meta["init"]
        self.ledger.append(
            {"step": "cobol-run", "program": prog["program_id"], "status": "start"}
        )
        try:
            for name, stmts in prog["paragraphs"]:
                self._exec_block(stmts)
        except StopRun:
            pass
        self.ledger.append(
            {
                "step": "cobol-run",
                "program": prog["program_id"],
                "status": "done",
                "statements": self.steps,
            }
        )
        return self.steps

    # ------------------------------------------------------------ exec
    def _exec_block(self, stmts: list):
        for s in stmts:
            self._exec(s)

    def _tick(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise BudgetExceeded(
                f"BUDGET EXCEEDED : {self.max_steps} instructions dépassées "
                f"(boucle infinie ? relance avec --max-steps N pour élargir)"
            )

    def _exec(self, s):
        self._tick()
        op = s[0]
        if op == "DISPLAY":
            print("".join(_fmt(self._atom(v)) for v in s[1]))
        elif op == "MOVE":
            _, src, targets = s
            value = self._atom(src)
            for t in targets:
                self._store(t, value)
        elif op == "COMPUTE":
            self._store(s[1], self._eval(s[2]))
        elif op == "ADD":
            _, operand, target, giving = s
            res = self._arith("+", self._get(target), self._eval(operand))
            self._store(giving if giving else target, res)
        elif op == "SUBTRACT":
            _, operand, target, giving = s
            res = self._arith("-", self._get(target), self._eval(operand))
            self._store(giving if giving else target, res)
        elif op == "MULTIPLY":
            _, operand, target, giving = s
            res = self._arith("*", self._get(target), self._eval(operand))
            self._store(giving if giving else target, res)
        elif op == "DIVIDE":
            _, mode, a, b, giving = s
            if mode == "INTO":
                res = self._arith("/", self._get(b), self._eval(a))
                self._store(giving if giving else b, res)
            else:
                res = self._arith("/", self._eval(a), self._eval(b))
                self._store(giving, res)
        elif op == "IF":
            _, cond, then_stmts, else_stmts = s
            if self._truth(cond):
                self._exec_block(then_stmts)
            else:
                self._exec_block(else_stmts)
        elif op == "EVALUATE":
            _, subject, branches, other = s
            value = self._eval(subject)
            for values, stmts in branches:
                if any(self._compare("=", value, self._atom(v)) for v in values):
                    self._exec_block(stmts)
                    return
            self._exec_block(other)
        elif op == "PERFORM":
            self._perform(s[1:])
        elif op == "STOP":
            raise StopRun()
        elif op == "SCAN-FILE":
            self._v_scan_file(s)
        elif op == "PROBE-FILE":
            self._v_probe_file(s)
        elif op == "PATCH-FILE":
            self._v_patch_file(s)
        elif op == "SWEEP-PATH":
            self._v_sweep(s)
        elif op == "REMEMBER":
            self._v_remember(s)
        elif op == "RECALL":
            self._v_recall(s)
        elif op == "ASK-GLM":
            self._v_ask_glm(s)
        elif op == "CONTEXT-LOAD":
            self._v_context_load(s)
        elif op == "CONTEXT-SEARCH":
            self._v_context_search(s)
        elif op == "NOTE-METRIC":
            self._v_note_metric(s)
        else:
            raise NexusRuntimeError(f"énoncé non implémenté : {op}")

    # ------------------------------------------------------------ control
    def _perform(self, args):
        kind = args[0]
        if kind == "para":
            self._call_para(args[1])
        elif kind == "para_times":
            n = int(self._atom(args[2]))
            for _ in range(n):
                self._call_para(args[1])
        elif kind == "para_until":
            while not self._truth(args[2]):
                self._call_para(args[1])
        elif kind == "para_varying":
            _, name, var, frm, by, cond = args
            val = self._eval(frm)
            while True:
                self._store(var, val)
                if self._truth(cond):
                    break
                self._call_para(name)
                val = self._arith("+", val, self._eval(by))
        elif kind == "inline_times":
            n = int(self._atom(args[1]))
            body = args[2]
            for _ in range(n):
                self._exec_block(body)
        elif kind == "inline_until":
            cond, body = args[1], args[2]
            while not self._truth(cond):
                self._exec_block(body)
        elif kind == "inline_varying":
            _, var, frm, by, cond, body = args
            val = self._eval(frm)
            while True:
                self._store(var, val)
                if self._truth(cond):
                    break
                self._exec_block(body)
                val = self._arith("+", val, self._eval(by))
        else:
            raise NexusRuntimeError(f"PERFORM inconnu : {kind}")

    def _call_para(self, name: str):
        if name not in self.paras:
            raise NexusRuntimeError(f"PARAGRAPHE INCONNU : {name}")
        self.depth += 1
        if self.depth > MAX_DEPTH:
            self.depth = 0
            raise NexusRuntimeError(
                f"PROFONDEUR PERFORM > {MAX_DEPTH} — récursion interdite"
            )
        try:
            self._exec_block(self.paras[name])
        finally:
            self.depth -= 1

    # ------------------------------------------------------------ values
    def _atom(self, atom):
        kind, val = atom
        if kind == "lit":
            return val
        return self._get(val)

    def _get(self, name: str):
        if name not in self.vars:
            raise NexusRuntimeError(f"VARIABLE NON DÉCLARÉE : {name}")
        return self.vars[name]

    def _store(self, name: str, value):
        if name not in self.data:
            raise NexusRuntimeError(f"VARIABLE NON DÉCLARÉE : {name}")
        meta = self.data[name]
        if meta["numeric"]:
            try:
                v = float(value)
            except (TypeError, ValueError):
                raise NexusRuntimeError(
                    f"{name} est PIC 9({meta['size']}) : valeur numérique "
                    f"attendue, reçu {value!r}"
                )
            v = int(v) if v.is_integer() else v
            if isinstance(v, int) and abs(v) >= 10 ** meta["size"]:
                v = v % (10 ** meta["size"])  # troncature COBOL
            self.vars[name] = v
        else:
            self.vars[name] = str(value)[: meta["size"]]

    def _arith(self, op: str, a, b):
        if isinstance(a, str) or isinstance(b, str):
            raise NexusRuntimeError(
                f"opération arithmétique {op} sur une chaîne : {a!r} {op} {b!r}"
            )
        try:
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if op == "/":
                if b == 0:
                    raise NexusRuntimeError("DIVISION PAR ZÉRO")
                return a / b
            if op == "**":
                return a ** b
        except OverflowError:
            raise NexusRuntimeError(f"débordement numérique : {a} {op} {b}")
        raise NexusRuntimeError(f"opérateur inconnu : {op}")

    def _eval(self, node):
        kind = node[0]
        if kind in ("lit", "num", "str"):
            return node[1]
        if kind == "var":
            return self._get(node[1])
        if kind == "neg":
            v = self._eval(node[1])
            if isinstance(v, str):
                raise NexusRuntimeError("négation d'une chaîne")
            return -v
        if kind == "bin":
            _, op, left, right = node
            return self._arith(op, self._eval(left), self._eval(right))
        raise NexusRuntimeError(f"expression inconnue : {node!r}")

    def _compare(self, op: str, a, b) -> bool:
        if isinstance(a, str) or isinstance(b, str):
            a, b = str(a), str(b)
        if op == "=":
            return a == b
        if op in ("<>", "!="):
            return a != b
        if op == ">":
            return a > b
        if op == "<":
            return a < b
        if op == ">=":
            return a >= b
        if op == "<=":
            return a <= b
        raise NexusRuntimeError(f"opérateur relationnel inconnu : {op}")

    def _truth(self, cond) -> bool:
        kind = cond[0]
        if kind == "cmp":
            _, op, left, right = cond
            return self._compare(op, self._eval(left), self._eval(right))
        if kind == "and":
            return self._truth(cond[1]) and self._truth(cond[2])
        if kind == "or":
            return self._truth(cond[1]) or self._truth(cond[2])
        raise NexusRuntimeError(f"condition inconnue : {cond!r}")

    # ------------------------------------------------------------ systemic verbs
    def _v_scan_file(self, s):
        _, path_a, reporting_a = s
        path = str(self._atom(path_a))
        result = self.scanner().scan(path)
        print(
            f"SCAN {path}: {result['count']} FINDINGS "
            f"({result['files_scanned']} FILES)"
        )
        if reporting_a is not None:
            out = str(self._atom(reporting_a))
            out_path = Path(out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"REPORT {out}")
        self.ledger.append(
            {"step": "cobol-scan", "path": path, "findings": result["count"],
             "status": "ok"}
        )

    def _v_probe_file(self, s):
        _, file_a, rule_a = s
        file = str(self._atom(file_a))
        rule = str(self._atom(rule_a))
        probe = self.gym().run(file, rule)
        print(f"PROBE {rule} {probe['status'].upper()}")
        self.ledger.append(
            {"step": "cobol-probe", "file": file, "rule": rule,
             "status": probe["status"]}
        )

    def _v_patch_file(self, s):
        _, file_a, rule_a = s
        file = str(self._atom(file_a))
        patcher = nexus_core.Patcher(self.ledger, self.gym())
        if rule_a is not None:
            rules = [str(self._atom(rule_a))]
        else:
            result = self.scanner().scan(file)
            rules = sorted({f["rule"] for f in result["findings"]})
            if not rules:
                print(f"PATCH rien à patcher sur {file}")
                return
        for rule in rules:
            res = patcher.patch(file, rule)
            line = f"PATCH {rule} {res['status'].upper()}"
            if res.get("strategy"):
                line += f" strategy={res['strategy']}"
            print(line)
            self.ledger.append(
                {"step": "cobol-patch", "file": file, "rule": rule,
                 "status": res["status"]}
            )

    def _v_sweep(self, s):
        _, path_a = s
        path = str(self._atom(path_a))
        rc = nexus_core.cmd_sweep(path, as_json=False)
        print(f"SWEEP exit={rc}")

    def _v_remember(self, s):
        _, key_a, value_a = s
        key = str(self._atom(key_a))
        value = self._atom(value_a)
        memory = self.memory()
        memory[key] = value
        (self.nexus_dir / "cobol_memory.json").write_text(
            json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _v_recall(self, s):
        _, key_a, into, show = s
        key = str(self._atom(key_a))
        memory = self.memory()
        if key not in memory:
            raise NexusRuntimeError(f"RECALL clé absente : {key!r}")
        value = memory[key]
        if into:
            self._store(into, value)
        if show or not into:
            print(_fmt(value))

    def _v_ask_glm(self, s):
        (_, q_a,) = s
        question = str(self._atom(q_a))
        try:
            answer = self.brain().ask(question)
        except (RuntimeError, Exception) as e:  # noqa: BLE001 — honnêteté
            raise NexusRuntimeError(f"ASK-GLM indisponible : {e}")
        print(f"[glm-advisory] {answer}")
        self.ledger.append({"step": "cobol-ask-glm", "status": "advisory"})

    def _v_context_load(self, s):
        _, path_a, limit = s
        path = str(self._atom(path_a))
        info = self.context().add_file(path, limit_tokens=limit)
        print(
            f"CONTEXT {path}: {info['tokens']} TOKENS ({info['chunks']} CHUNKS) "
            f"capacity={self.context().max_tokens}"
        )

    def _v_context_search(self, s):
        (_, q_a,) = s
        query = str(self._atom(q_a))
        hits = self.context().search(query)
        if not hits:
            print("HIT aucune correspondance")
            return
        for h in hits:
            print(f"HIT score={h['score']} doc={h['doc']} {h['excerpt']}")

    def _v_note_metric(self, s):
        _, name_a, expr = s
        name = str(self._atom(name_a))
        value = self._eval(expr)
        metrics = self.metrics()
        metrics.setdefault(name, []).append(
            {"value": value, "ts": __import__("datetime").datetime.now().isoformat()}
        )
        (self.nexus_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ------------------------------------------------------------------ CLI
def run_file(path: str, max_steps: int = DEFAULT_MAX_STEPS, as_json: bool = False) -> int:
    try:
        tokens = lex_file(path)
    except OSError as e:
        print(f"ERREUR FICHIER : {e}", file=sys.stderr)
        return 1
    except SyntaxError as e:
        print(f"ERREUR SYNTAXE (lexer) : {e}", file=sys.stderr)
        return 2
    try:
        prog = Parser(tokens).parse_program()
    except NexusSyntaxError as e:
        print(f"ERREUR SYNTAXE : {e}", file=sys.stderr)
        return 2
    machine = Machine(max_steps=max_steps)
    try:
        statements = machine.run(prog)
    except BudgetExceeded as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        return 3
    except NexusRuntimeError as e:
        print(f"ERREUR EXECUTION : {e}", file=sys.stderr)
        return 1
    if as_json:
        print(
            json.dumps(
                {
                    "program": prog["program_id"],
                    "statements": statements,
                    "exit": "ok",
                    "language": f"NEXUS-COBOL v{VERSION}",
                },
                ensure_ascii=False,
            )
        )
    return 0


def main(argv: list) -> int:
    args = argv[1:]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    max_steps = DEFAULT_MAX_STEPS
    as_json = "--json" in args
    if "--max-steps" in args:
        i = args.index("--max-steps")
        if i + 1 < len(args):
            max_steps = int(args[i + 1])
    return run_file(path, max_steps=max_steps, as_json=as_json)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
