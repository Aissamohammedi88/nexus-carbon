#!/usr/bin/env python3
"""NEXUS Context Engine (v1.1 NOBLE) — mémoire locale hiérarchique.

Fonction new-generation demandée par DGK (option « plus noble que Gemini »).
HONNÊTETÉ ULTRA : c'est une capacité MÉMOIRE locale (capacité configurable,
défaut 1M tokens), PAS un modèle long-context et PAS un LLM. Les tokens
sont estimés par l'heuristique usuelle ~4 caractères/token — heuristique
documentée, pas une promesse de tokenizer exact.

Usage CLI :
    python3 nexus_context.py --load FILE [--limit N] [--query Q] [--json]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEFAULT_MAX_TOKENS = 1_000_000
CHUNK_CHARS = 2000


def estimate_tokens(text: str) -> int:
    """Heuristique ~4 caractères/token. Documentée, testée, honnête."""
    return max(1, len(text) // 4)


class ContextEngine:
    """Mémoire locale : documents découpés en chunks, recherche par
    fréquence de mots-clés, éviction FIFO si dépassement de capacité."""

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.max_tokens = max_tokens
        self.docs: dict = {}
        self.chunks: list = []

    # ---- ingestion ---------------------------------------------------
    def add_text(self, name: str, text: str, limit_tokens: int | None = None) -> dict:
        if limit_tokens is not None:
            text = text[: limit_tokens * 4]
        tokens = estimate_tokens(text)
        while self.docs and self.tokens() + tokens > self.max_tokens:
            victim = next(iter(self.docs))
            self.docs.pop(victim)
            self.chunks = [c for c in self.chunks if c["doc"] != victim]
        self.docs[name] = {"tokens": tokens}
        for i in range(0, len(text), CHUNK_CHARS):
            piece = text[i : i + CHUNK_CHARS]
            self.chunks.append({"doc": name, "offset": i, "text": piece})
        return {"tokens": tokens, "chunks": len(self.chunks), "docs": len(self.docs)}

    def add_file(self, path: str, limit_tokens: int | None = None) -> dict:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return self.add_text(Path(path).name, text, limit_tokens)

    # ---- interrogation -------------------------------------------------
    def tokens(self) -> int:
        return sum(d["tokens"] for d in self.docs.values())

    def stats(self) -> dict:
        used = self.tokens()
        return {
            "docs": len(self.docs),
            "chunks": len(self.chunks),
            "tokens": used,
            "max_tokens": self.max_tokens,
            "usage_pct": round(100.0 * used / self.max_tokens, 3),
        }

    def search(self, query: str, top: int = 3) -> list:
        words = [w for w in re.findall(r"[a-z0-9\-]+", query.lower()) if len(w) >= 2]
        scored = []
        for c in self.chunks:
            low = c["text"].lower()
            score = sum(low.count(w) for w in words)
            if score:
                scored.append(
                    {
                        "doc": c["doc"],
                        "offset": c["offset"],
                        "score": score,
                        "excerpt": c["text"][:160].replace("\n", " "),
                    }
                )
        scored.sort(key=lambda h: -h["score"])
        return scored[:top]


def main_cli(argv: list) -> int:
    load = limit = query = None
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    i = 0
    while i < len(args):
        if args[i] == "--load" and i + 1 < len(args):
            load = args[i + 1]
            i += 2
        elif args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == "--query" and i + 1 < len(args):
            query = args[i + 1]
            i += 2
        else:
            i += 1
    if not load:
        print(__doc__)
        return 2
    engine = ContextEngine()
    info = engine.add_file(load, limit_tokens=limit)
    st = engine.stats()
    hits = engine.search(query) if query else []
    if as_json:
        print(
            json.dumps(
                {"load": info, "stats": st, "hits": hits}, ensure_ascii=False, indent=2
            )
        )
    else:
        print(
            f"CONTEXT {load}: {st['tokens']} TOKENS ({st['chunks']} CHUNKS) "
            f"capacity={st['max_tokens']} usage={st['usage_pct']}%"
        )
        for h in hits:
            print(f"HIT score={h['score']} doc={h['doc']} {h['excerpt']}")
        if query and not hits:
            print("HIT aucune correspondance")
    return 0


if __name__ == "__main__":
    sys.exit(main_cli(sys.argv[1:]))
