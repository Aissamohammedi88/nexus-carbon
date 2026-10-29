#!/usr/bin/env python3
"""
GPTNexus v1.0.0 "Carbon Heart" — DGK x GLM, protocole ULTRA.

Skeleton : llama-coder style — thin bash launcher (gptnexus.sh) + CLI core.
Monster : la logique du spec Gemini 4 Carbon de DGK, appliquée pour de vrai :

    Finding        -> nexus_scan (Rust natif, module scanner/)
    ExploitGym     -> ExploitGym (sondes contrôlées, preuve d'exploitabilité)
    Patching       -> Patcher (stratégies multiples + persistance)
    Long-horizon   -> Ledger (.nexus/mission.json : étapes, impasses, budget)
    Anti-halluc.   -> [nexus-proof] vs [glm-advisory] : seul le banc prouve

PROTOCOLE ULTRA (docs/ULTRA.md) :
    U - Unfiltered    : chaque écart déclaré dans AUDIT.md, aucun abandon silencieux
    L - Long-horizon  : le registre exige une impasse traversée avant le succès
    T - Test-proof    : chaque capacité a un test qui l'exécute (N01-N13)
    R - Rust-core     : le scanner est du Rust stdlib-only
    A - Autonomous     : sweep = scan -> exploit -> patch -> verify sans humain

Ce que ce n'est PAS (honnêteté ULTRA) : pas un modèle à 1M tokens, pas
SEC-bench Pro 88.2%, pas d'autonomie multi-jours. Les chiffres du spec
de DGK restent dans docs/gemini_carbon_spec_dgk.md ; les nôtres sont
mesurés par le banc tests/nexus_edge_tests.sh.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

NEXUS_HOME = Path(__file__).resolve().parent
SCAN_BIN = NEXUS_HOME / "scanner" / "target" / "release" / "nexus_scan"

VERSION = "1.1.0"
CODENAME = "NOBLE"
PROTOCOL = (
    "ULTRA v1.0 (U-nfiltered, L-ong-horizon, T-est-proof, R-ust-core, A-utonomous)"
)

LABEL_PROOF = "[nexus-proof]"
LABEL_ADVISORY = "[glm-advisory]"
LABEL_INFO = "[nexus]"


def say(msg: str) -> None:
    print(f"{LABEL_INFO} {msg}")


def proof(msg: str) -> None:
    print(f"{LABEL_PROOF} {msg}")


# ============================================================
# §1 LEDGER — le registre de mission (Long-horizon, ULTRA: L)
# ============================================================


class Ledger:
    """Registre de mission JSON. Chaque étape y est consignée, y compris
    les impasses (dead ends) : la persistance n'est prouvée que si le
    banc voit une impasse traversée AVANT un succès final."""

    def __init__(self, root: str | Path):
        self.dir = Path(root) / ".nexus"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "mission.json"
        self._state = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "mission_id": f"nexus-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "started": datetime.now(timezone.utc).isoformat(),
            "protocol": PROTOCOL,
            "steps": [],
            "dead_ends": 0,
            "budget_used": 0,
            "final": None,
        }

    def append(self, step: dict) -> None:
        step["ts"] = datetime.now(timezone.utc).isoformat()
        self._state["steps"].append(step)
        if step.get("status") == "dead_end":
            self._state["dead_ends"] += 1
        if step.get("step") == "patch":
            self._state["budget_used"] += 1
        self._state["updated"] = step["ts"]
        self.save()

    def set_final(self, final: str) -> None:
        self._state["final"] = final
        self.save()

    @property
    def state(self) -> dict:
        return self._state

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False), encoding="utf-8"
        )


# ============================================================
# §2 SCANNER — Finding (module Rust, ULTRA: R)
# ============================================================


class Scanner:
    """Wrapper du binaire Rust nexus_scan. Le scanner ne ment pas :
    il sort du JSON, le banc le vérifie."""

    def __init__(self, binary: Path = SCAN_BIN):
        self.binary = binary
        if not self.binary.exists():
            raise FileNotFoundError(
                f"nexus_scan introuvable : {self.binary} — lance ./gptnexus.sh build"
            )

    def scan(self, path: str) -> dict:
        proc = subprocess.run(
            [str(self.binary), path], capture_output=True, text=True, timeout=60
        )
        if proc.returncode != 0:
            raise RuntimeError(f"nexus_scan a échoué : {proc.stderr.strip()}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"nexus_scan a sorti un JSON invalide : {e}")

    def human_summary(self, result: dict) -> str:
        lines = []
        for f in result["findings"]:
            lines.append(
                f"  {f['id']} {f['rule']:12s} {f['severity']:8s} "
                f"{f['file']}:{f['line']}  {f['snippet'][:60]}"
            )
        if not lines:
            lines.append("  aucune détection")
        return "\n".join(lines)


# ============================================================
# §3 EXPLOIT GYM — sondes contrôlées (ULTRA: T)
# ============================================================


class ExploitGym:
    """Sondes contrôlées et INOFFENSIVES : elles prouvent l'exploitabilité
    sans casser quoi que ce soit. Un finding non confirmé n'est jamais
    patché à l'aveugle (ULTRA : ne jamais affirmer sans sonder)."""

    EVAL_PAYLOAD = '__import__("os").getpid()'
    SQL_PAYLOAD = "1 OR 1=1"

    def _run(
        self, file: str, arg: str, timeout: int = 10
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", file, arg], capture_output=True, text=True, timeout=timeout
        )

    def probe_eval(self, file: str) -> dict:
        proc = self._run(file, self.EVAL_PAYLOAD)
        out = proc.stdout.strip()
        if proc.returncode == 0 and out.isdigit():
            return {
                "rule": "eval",
                "status": "confirmed",
                "evidence": f"charge '__import__' exécutée : pid={out} retourné "
                f"(exécution de code arbitraire prouvée)",
            }
        if proc.returncode != 0:
            return {
                "rule": "eval",
                "status": "blocked",
                "evidence": f"charge rejetée (exit={proc.returncode}) : "
                f"{(proc.stderr.strip().splitlines() or ['?'])[-1][:80]}",
            }
        return {
            "rule": "eval",
            "status": "inconclusive",
            "evidence": f"exit=0 mais sortie non numérique : {out[:60]!r}",
        }

    def probe_sql(self, file: str) -> dict:
        proc = self._run(file, self.SQL_PAYLOAD)
        out = proc.stdout
        if "WHERE id = 1 OR 1=1" in out:
            return {
                "rule": "sql_concat",
                "status": "confirmed",
                "evidence": "l'entrée '1 OR 1=1' a modifié la requête SQL "
                "(injection confirmée)",
            }
        if "WHERE id = ?" in out and "WHERE id = 1 OR 1=1" not in out:
            return {
                "rule": "sql_concat",
                "status": "blocked",
                "evidence": "l'entrée est isolée dans les paramètres, la requête "
                "SQL reste 'WHERE id = ?'",
            }
        return {
            "rule": "sql_concat",
            "status": "inconclusive",
            "evidence": f"sortie inattendue : {out.strip()[:60]!r}",
        }

    def probe_dyn_import(self, file: str) -> dict:
        proc = self._run(file, "os")
        out = proc.stdout.strip()
        if "loaded os" in out:
            return {
                "rule": "dyn_import",
                "status": "confirmed",
                "evidence": "module arbitraire 'os' chargé dynamiquement",
            }
        if proc.returncode != 0:
            return {
                "rule": "dyn_import",
                "status": "blocked",
                "evidence": f"chargement refusé (exit={proc.returncode}) : "
                f"{(proc.stderr.strip().splitlines() or ['?'])[-1][:80]}",
            }
        return {
            "rule": "dyn_import",
            "status": "inconclusive",
            "evidence": f"sortie inattendue : {out[:60]!r}",
        }

    def run(self, file: str, rule: str) -> dict:
        probes = {
            "eval": self.probe_eval,
            "sql_concat": self.probe_sql,
            "dyn_import": self.probe_dyn_import,
        }
        fn = probes.get(rule)
        if fn is None:
            return {
                "rule": rule,
                "status": "inconclusive",
                "evidence": "aucune sonde implémentée pour cette règle (v1.0 : "
                "eval, sql_concat, dyn_import)",
            }
        result = fn(file)
        result["file"] = file
        return result


# ============================================================
# §4 PATCHER — stratégies + persistance (ULTRA: L + T)
# ============================================================

SAFE_EVAL_BLOCK = """# [nexus-patch] strategy ast_whitelist_safeeval — injected by GPTNexus
# Même logique que PROTON-Calc de DGK : évaluateur AST à liste blanche.
import ast as _n_ast


def _nexus_safe_eval(expr):
    _allowed_bin = (_n_ast.Add, _n_ast.Sub, _n_ast.Mult, _n_ast.Div,
                    _n_ast.FloorDiv, _n_ast.Mod, _n_ast.Pow)
    _allowed_un = (_n_ast.USub, _n_ast.UAdd)

    def _ev(node):
        if isinstance(node, _n_ast.Expression):
            return _ev(node.body)
        if isinstance(node, _n_ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, _n_ast.BinOp):
            if not isinstance(node.op, _allowed_bin):
                raise ValueError("nexus_safe_eval: operator not allowed")
            left = _ev(node.left)
            right = _ev(node.right)
            if isinstance(node.op, _n_ast.Add):
                return left + right
            if isinstance(node.op, _n_ast.Sub):
                return left - right
            if isinstance(node.op, _n_ast.Mult):
                return left * right
            if isinstance(node.op, _n_ast.Div):
                return left / right
            if isinstance(node.op, _n_ast.FloorDiv):
                return left // right
            if isinstance(node.op, _n_ast.Mod):
                return left % right
            if isinstance(node.op, _n_ast.Pow):
                return left ** right
        if isinstance(node, _n_ast.UnaryOp) and isinstance(node.op, _allowed_un):
            val = _ev(node.operand)
            return -val if isinstance(node.op, _n_ast.USub) else val
        raise ValueError("nexus_safe_eval: expression not allowed")

    return _ev(_n_ast.parse(expr, mode="eval"))
"""

WHITELIST_IMPORT_BLOCK = """# [nexus-patch] strategy whitelist_importlib — injected by GPTNexus
import importlib as _n_importlib

_NEXUS_ALLOWED_MODULES = ("math", "json", "statistics")


def _nexus_import(name):
    if name not in _NEXUS_ALLOWED_MODULES:
        raise ImportError("module not whitelisted by nexus: %r" % (name,))
    return _n_importlib.import_module(name)
"""


def _insert_code(content: str, block: str) -> str:
    """Insère le bloc injecté juste avant la première ligne d'import
    top-level (portée v1.0 : fichiers de la taille des fixtures)."""
    lines = content.split("\n")
    idx = 0
    for i, ln in enumerate(lines):
        if ln.startswith("import ") or ln.startswith("from "):
            idx = i
            break
    lines.insert(idx, block)
    return "\n".join(lines)


class Patcher:
    """Moteur de patch à stratégies multiples. La persistance est
    ARCHITECTURALE : si une stratégie échoue à la vérification, l'échec
    est consigné comme impasse (dead end) et la suivante est essayée.
    Le banc N09 exige >= 1 impasse AVANT un succès final."""

    def __init__(self, ledger: Ledger, gym: ExploitGym):
        self.ledger = ledger
        self.gym = gym

    # ---- stratégies par règle -------------------------------------
    @staticmethod
    def _patch_eval_literal(content: str) -> tuple[str | None, str | None]:
        if not re.search(r"\beval\(", content):
            return None, "motif eval( introuvable"
        new = re.sub(r"\beval\((\w+)\)", r"ast.literal_eval(\1)", content)
        if "import ast" not in new:
            new = _insert_code(new, "import ast  # [nexus-patch] strategy literal_eval")
        return new, None

    @staticmethod
    def _patch_eval_safe(content: str) -> tuple[str | None, str | None]:
        if not re.search(r"\beval\((\w+)\)", content):
            return None, "motif eval(<mot>) introuvable"
        new = re.sub(r"\beval\((\w+)\)", r"_nexus_safe_eval(\1)", content)
        new = _insert_code(new, SAFE_EVAL_BLOCK)
        return new, None

    @staticmethod
    def _patch_sql_param(content: str) -> tuple[str | None, str | None]:
        if not re.search(r'"(SELECT[^"]*)"\s*\+\s*(\w+)', content):
            return None, 'motif "SELECT..." + var introuvable'
        new = re.sub(
            r'"(SELECT[^"]*)"\s*\+\s*(\w+)',
            r'("\g<1>?", (\g<2>,))',
            content,
        )
        return new, None

    @staticmethod
    def _patch_import_whitelist(content: str) -> tuple[str | None, str | None]:
        if not re.search(r"__import__\((\w+)\)", content):
            return None, "motif __import__(<mot>) introuvable"
        new = re.sub(r"__import__\((\w+)\)", r"_nexus_import(\1)", content)
        new = _insert_code(new, WHITELIST_IMPORT_BLOCK)
        return new, None

    STRATEGIES = {
        "eval": [
            ("literal_eval", _patch_eval_literal.__func__),
            ("ast_whitelist_safeeval", _patch_eval_safe.__func__),
        ],
        "sql_concat": [
            ("parameterize", _patch_sql_param.__func__),
        ],
        "dyn_import": [
            ("whitelist_importlib", _patch_import_whitelist.__func__),
        ],
    }

    # ---- vérification (ULTRA: T — preuve, pas promesse) -------------
    def _legit_check(self, file: str, rule: str) -> tuple[bool, str]:
        try:
            if rule == "eval":
                proc = subprocess.run(
                    ["python3", file, "1+1"], capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0 and proc.stdout.strip() == "2":
                    return True, "usage légitime préservé : '1+1' -> 2"
                last = (proc.stderr.strip().splitlines() or ["?"])[-1][:70]
                return False, f"usage légitime cassé : '1+1' ne renvoie pas 2 ({last})"

            if rule == "sql_concat":
                proc = subprocess.run(
                    ["python3", file, "5"], capture_output=True, text=True, timeout=10
                )
                if (
                    proc.returncode == 0
                    and "WHERE id = ?" in proc.stdout
                    and "5" in proc.stdout
                ):
                    return (
                        True,
                        "usage légitime préservé : get_user(5) -> requête paramétrée",
                    )
                return (
                    False,
                    "usage légitime cassé : get_user(5) ne renvoie pas une requête paramétrée",
                )

            if rule == "dyn_import":
                proc = subprocess.run(
                    ["python3", file, "math"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if proc.returncode == 0 and "loaded math" in proc.stdout:
                    return True, "usage légitime préservé : load_module('math') OK"
                return False, "usage légitime cassé : load_module('math') en échec"

            return False, f"aucune vérification d'usage légitime pour {rule} (v1.0)"
        except subprocess.TimeoutExpired:
            return False, "timeout pendant la vérification d'usage légitime"

    def verify(self, file: str, rule: str) -> tuple[bool, str]:
        comp = subprocess.run(
            ["python3", "-m", "py_compile", file], capture_output=True, timeout=15
        )
        if comp.returncode != 0:
            return False, "la compilation du fichier patché échoue"

        probe = self.gym.run(file, rule)
        if probe["status"] == "confirmed":
            return False, "l'exploit est TOUJOURS confirmé après patch"
        if probe["status"] == "inconclusive":
            return False, "sonde non concluante après patch"

        ok, reason = self._legit_check(file, rule)
        if not ok:
            return False, reason
        return True, "compile OK + exploit bloqué + usage légitime préservé"

    # ---- boucle de persistance -------------------------------------
    def patch(self, file: str, rule: str) -> dict:
        path = Path(file)
        backup = path.with_suffix(path.suffix + ".bak")
        strategies = self.STRATEGIES.get(rule)
        if not strategies:
            self.ledger.append(
                {
                    "step": "patch",
                    "file": file,
                    "rule": rule,
                    "status": "not_applicable",
                    "reason": "aucune stratégie pour cette règle (v1.0)",
                }
            )
            return {
                "file": file,
                "rule": rule,
                "status": "no_strategy",
                "dead_ends": [],
            }

        original = path.read_text(encoding="utf-8")
        shutil.copy2(path, backup)

        dead_ends: list[dict] = []
        for name, fn in strategies:
            new_content, err = fn(original)
            if new_content is None:
                dead_ends.append({"strategy": name, "reason": err})
                self.ledger.append(
                    {
                        "step": "patch",
                        "file": file,
                        "rule": rule,
                        "strategy": name,
                        "status": "dead_end",
                        "reason": err,
                    }
                )
                continue
            path.write_text(new_content, encoding="utf-8")
            ok, reason = self.verify(str(path), rule)
            if ok:
                self.ledger.append(
                    {
                        "step": "patch",
                        "file": file,
                        "rule": rule,
                        "strategy": name,
                        "status": "success",
                        "reason": reason,
                    }
                )
                return {
                    "file": file,
                    "rule": rule,
                    "status": "success",
                    "strategy": name,
                    "dead_ends": dead_ends,
                }
            dead_ends.append({"strategy": name, "reason": reason})
            self.ledger.append(
                {
                    "step": "patch",
                    "file": file,
                    "rule": rule,
                    "strategy": name,
                    "status": "dead_end",
                    "reason": reason,
                }
            )

        # épuisement du budget : restauration honnête
        path.write_text(original, encoding="utf-8")
        backup.unlink(missing_ok=True)
        self.ledger.append(
            {
                "step": "patch",
                "file": file,
                "rule": rule,
                "status": "budget_exhausted",
                "dead_ends": [d["strategy"] for d in dead_ends],
            }
        )
        return {"file": file, "rule": rule, "status": "failed", "dead_ends": dead_ends}


# ============================================================
# §5 GLM BRAIN — cerveau consultatif (famille DGK x GLM)
# ============================================================


class GLMBrain:
    """Le membre glm [ai-brain] de la famille, branché en vrai via le CLI
    z-ai. ULTRA: T — GLM émet des AVIS ([glm-advisory]), jamais des
    preuves. Seul le banc émet des preuves ([nexus-proof])."""

    def __init__(self):
        self.cli = shutil.which("z-ai")

    def ask(self, prompt: str, system: str | None = None, timeout: int = 180) -> str:
        if not self.cli:
            raise RuntimeError("CLI z-ai introuvable — GLM indisponible")
        out_path = (
            Path(tempfile.gettempdir())
            / f"nexus_glm_{os.getpid()}_{int(time.time())}.json"
        )
        cmd = [self.cli, "chat", "-p", prompt]
        if system:
            cmd += ["-s", system]
        cmd += ["-o", str(out_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"z-ai a échoué : {proc.stderr.strip()[:120]}")
        data = json.loads(out_path.read_text(encoding="utf-8"))
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        if not content.strip():
            raise RuntimeError("GLM a répondu vide")
        return content

    def brief(self, scan_result: dict) -> str:
        system = (
            "Tu es l'auditeur sécurité de GPTNexus. Tu réponds en français, "
            "de façon directe et sans jargon inutile."
        )
        prompt = (
            "Voici le résultat JSON d'un scan de sécurité de mon code :\n"
            f"{json.dumps(scan_result, ensure_ascii=False)}\n\n"
            "Résume en 5 lignes maximum, en français simple : quelles failles "
            "ont été détectées, leur sévérité, et le correctif recommandé."
        )
        return self.ask(prompt, system=system)


# ============================================================
# §6 PIPELINE SWEEP — autonomie (ULTRA: A)
# ============================================================


def cmd_sweep(path: str, as_json: bool = False) -> int:
    scanner = Scanner()
    root = Path(path)
    ledger_root = root if root.is_dir() else root.parent
    ledger = Ledger(ledger_root)
    gym = ExploitGym()
    patcher = Patcher(ledger, gym)

    result = scanner.scan(path)
    ledger.append(
        {
            "step": "scan",
            "path": path,
            "findings": result["count"],
            "files": result["files_scanned"],
        }
    )

    confirmed: list[tuple[str, str]] = []
    for f in result["findings"]:
        probe = gym.run(f["file"], f["rule"])
        ledger.append(
            {
                "step": "exploit",
                "file": f["file"],
                "rule": f["rule"],
                "status": probe["status"],
                "evidence": probe["evidence"],
            }
        )
        if probe["status"] == "confirmed":
            confirmed.append((f["file"], f["rule"]))

    patched_ok = True
    for file, rule in confirmed:
        pres = patcher.patch(file, rule)
        if pres["status"] != "success":
            patched_ok = False

    rescan = scanner.scan(path)
    ledger.append({"step": "rescan", "path": path, "findings": rescan["count"]})

    rules_remaining = {(f["file"], f["rule"]) for f in rescan["findings"]}
    leaked = [f"{f} :: {r}" for f, r in confirmed if (f, r) in rules_remaining]
    final = (
        "success" if (patched_ok and not leaked and rescan["count"] == 0) else "partial"
    )
    ledger.set_final(final)

    if as_json:
        print(
            json.dumps(
                {
                    "path": path,
                    "findings_initial": result["count"],
                    "confirmed": len(confirmed),
                    "rescan": rescan["count"],
                    "final": final,
                    "ledger": str(ledger.path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        proof(
            f"sweep terminé : {result['count']} findings -> {len(confirmed)} confirmés "
            f"-> rescan {rescan['count']} restant(s) -> final={final}"
        )
        if leaked:
            say(f"règles non neutralisées : {leaked}")
        say(f"registre de mission : {ledger.path}")
    return 0 if final == "success" else 1


# ============================================================
# §7 COMMANDES CLI
# ============================================================


def cmd_scan(path: str, as_json: bool = False) -> int:
    scanner = Scanner()
    result = scanner.scan(path)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        say(
            f"scan de {path} : {result['files_scanned']} fichier(s), "
            f"{result['count']} détection(s)"
        )
        print(scanner.human_summary(result))
    return 0


def cmd_exploit(file: str, rule: str, as_json: bool = False) -> int:
    gym = ExploitGym()
    probe = gym.run(file, rule)
    if as_json:
        print(json.dumps(probe, ensure_ascii=False, indent=2))
    else:
        label = {
            "confirmed": "CONFIRMÉ",
            "blocked": "BLOQUÉ",
            "inconclusive": "NON CONCLUANT",
        }
        proof(f"sonde {rule} sur {file} : {label.get(probe['status'], '?')}")
        say(f"preuve : {probe['evidence']}")
    return 0 if probe["status"] in ("confirmed", "blocked") else 1


def cmd_patch(file: str, rule: str | None, as_json: bool = False) -> int:
    path = Path(file)
    if rule is None:
        scanner = Scanner()
        result = scanner.scan(file)
        rules = sorted({f["rule"] for f in result["findings"]})
        if not rules:
            say(f"aucun finding sur {file} — rien à patcher")
            return 0
        say(f"règles auto-détectées : {rules}")
    else:
        rules = [rule]

    ledger = Ledger(path.parent)
    gym = ExploitGym()
    patcher = Patcher(ledger, gym)

    overall = "success"
    all_results = []
    for r in rules:
        res = patcher.patch(file, r)
        all_results.append(res)
        if res["status"] != "success":
            overall = "failed"
    ledger.set_final(overall if rules else "nothing_to_do")

    if as_json:
        print(
            json.dumps(
                {"file": file, "results": all_results, "final": overall},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for res in all_results:
            if res["status"] == "success":
                proof(
                    f"patch {res['rule']} RÉUSSI via {res['strategy']} "
                    f"(impasses traversées : {len(res['dead_ends'])})"
                )
                for d in res["dead_ends"]:
                    say(f"impasse {d['strategy']} : {d['reason']}")
            else:
                say(f"patch {res.get('rule')} ÉCHOUÉ — impasses : {res['dead_ends']}")
        say(f"registre : {ledger.path}")
    return 0 if overall == "success" else 1


def cmd_verify(file: str, rule: str) -> int:
    ledger = Ledger(Path(file).parent)
    patcher = Patcher(ledger, ExploitGym())
    ok, reason = patcher.verify(file, rule)
    if ok:
        proof(f"vérification {rule} sur {file} : {reason}")
        return 0
    say(f"vérification {rule} ÉCHOUÉE : {reason}")
    return 1


def cmd_ask(question: str) -> int:
    brain = GLMBrain()
    try:
        answer = brain.ask(question)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        say(f"GLM indisponible : {e}")
        return 1
    print(f"{LABEL_ADVISORY} {answer}")
    say("avis consultatif — les preuves viennent du banc, pas du cerveau (ULTRA: T)")
    return 0


def cmd_brief(path: str) -> int:
    scanner = Scanner()
    result = scanner.scan(path)
    say(
        f"scan : {result['count']} détection(s) sur {result['files_scanned']} fichier(s)"
    )
    brain = GLMBrain()
    try:
        answer = brain.brief(result)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        say(f"GLM indisponible : {e}")
        return 1
    print(f"{LABEL_ADVISORY} {answer}")
    say("l'analyse GLM est un avis ; les findings ci-dessus sont des preuves de scan")
    return 0


def cmd_mission(directory: str = ".") -> int:
    ledger = Ledger(directory)
    print(json.dumps(ledger.state, ensure_ascii=False, indent=2))
    return 0


def cmd_cobol(path: str, max_steps: int = 200_000, as_json: bool = False) -> int:
    """Exécuter un programme NEXUS-COBOL (Language Systémique, v1.1 NOBLE)."""
    import nexus_cobol

    return nexus_cobol.run_file(path, max_steps=max_steps, as_json=as_json)


def cmd_context(args: list) -> int:
    """Mémoire locale hiérarchique (fonction new-generation v1.1 NOBLE)."""
    import nexus_context

    return nexus_context.main_cli(args)


def cmd_version() -> int:
    print(f'GPTNexus v{VERSION} "{CODENAME}" — DGK x GLM')
    print(f"           (Carbon Heart + Language Systémique NEXUS-COBOL)")
    print(f"protocole : {PROTOCOL}")
    print(f"langage   : NEXUS-COBOL v1.1 — verbes COBOL + verbes systémiques")
    print(f"mémoire   : ContextEngine local 1M tokens (heuristique 4 chars/token)")
    if SCAN_BIN.exists():
        proc = subprocess.run(
            [str(SCAN_BIN), "--version"], capture_output=True, text=True
        )
        print(f"scanner   : {proc.stdout.strip()}")
    else:
        print("scanner   : non compilé (./gptnexus.sh build)")
    print("brain     : GLM via CLI z-ai (advisory only)")
    return 0


HELP = f"""GPTNexus v{VERSION} "{CODENAME}" — DGK x GLM, protocole ULTRA
(Carbon Heart + Language Systémique NEXUS-COBOL — l'option noble demandée par DGK)

USAGE
  gptnexus.sh <commande> [args]

COMMANDES CORE (v1.0 Carbon Heart)
  build                     compiler le scanner Rust (nexus_scan)
  scan <path> [--json]      scanner un fichier/répertoire (Finding)
  exploit <file> <rule>     sonder une faille de façon contrôlée (ExploitGym)
                            règles v1.0 : eval, sql_concat, dyn_import
  patch <file> [rule]       patcher avec persistance (stratégies + impasses)
  verify <file> <rule>      vérifier compile + exploit bloqué + usage légitime
  sweep <path> [--json]     pipeline complet autonome : scan->exploit->patch->rescan
  ask "<question>"          demander un avis au cerveau GLM ([glm-advisory])
  brief <path>              brief sécurité en français par GLM
  mission [dir]             afficher le registre de mission (.nexus/mission.json)

COMMANDES NOBLE (v1.1 — Language Systémique + new-generation)
  cobol <file.nxc> [--max-steps N] [--json]
                            exécuter un programme NEXUS-COBOL : verbes COBOL
                            + verbes systémiques (SCAN-FILE, PROBE-FILE,
                            PATCH-FILE, SWEEP-PATH, REMEMBER, RECALL, ASK-GLM,
                            CONTEXT-LOAD, CONTEXT-SEARCH, NOTE-METRIC)
  context --load F [--limit N] [--query Q] [--json]
                            mémoire locale hiérarchique (capacité 1M tokens,
                            heuristique ~4 chars/token — PAS un LLM long-context)

PROTOCOLE ULTRA
  U-nfiltered    aucun écart caché, AUDIT.md dit tout
  L-ong-horizon  le registre doit montrer une impasse traversée avant succès
  T-est-proof    [nexus-proof] = prouvé par exécution, [glm-advisory] = avis
  R-ust-core     le scanner est natif Rust stdlib-only
  A-utonomous    sweep enchaîne tout seul, budget consigné au registre
"""


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        print(HELP)
        return 0
    cmd, rest = args[0], args[1:]
    as_json = "--json" in rest
    rest = [a for a in rest if a != "--json"]

    try:
        if cmd == "scan" and rest:
            return cmd_scan(rest[0], as_json)
        if cmd == "exploit" and len(rest) >= 2:
            return cmd_exploit(rest[0], rest[1], as_json)
        if cmd == "patch" and rest:
            return cmd_patch(rest[0], rest[1] if len(rest) > 1 else None, as_json)
        if cmd == "verify" and len(rest) >= 2:
            return cmd_verify(rest[0], rest[1])
        if cmd == "sweep" and rest:
            return cmd_sweep(rest[0], as_json)
        if cmd == "ask" and rest:
            return cmd_ask(" ".join(rest))
        if cmd == "brief" and rest:
            return cmd_brief(rest[0])
        if cmd == "mission":
            return cmd_mission(rest[0] if rest else ".")
        if cmd == "cobol" and rest:
            max_steps = 200_000
            if "--max-steps" in rest:
                idx = rest.index("--max-steps")
                if idx + 1 < len(rest):
                    max_steps = int(rest[idx + 1])
            return cmd_cobol(rest[0], max_steps, as_json)
        if cmd == "context":
            return cmd_context(rest)
        if cmd == "version":
            return cmd_version()
        if cmd in ("help", "--help", "-h"):
            print(HELP)
            return 0
        print(HELP)
        return 2
    except FileNotFoundError as e:
        say(f"erreur : {e}")
        return 1
    except subprocess.TimeoutExpired:
        say("timeout d'un sous-processus — relance ou vérifie le fichier")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
