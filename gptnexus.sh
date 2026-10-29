#!/usr/bin/env bash
# GPTNexus v1.0.0 "Carbon Heart" — bash launcher (squelette llama-coder style)
# DGK x GLM — protocole ULTRA. Le bash appelle les autres langues :
# Rust (scanner natif) + Python (cerveau orchestrateur) + GLM (avis via z-ai).
set -euo pipefail

NX_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCAN_BIN="$NX_HOME/scanner/target/release/nexus_scan"

export PATH="$HOME/.cargo/bin:$PATH"

c_red()    { printf '\033[31m%s\033[0m' "$*"; }
c_green()  { printf '\033[32m%s\033[0m' "$*"; }
c_cyan()   { printf '\033[36m%s\033[0m' "$*"; }

say() { c_cyan "gptnexus:"; printf ' %s\n' "$*"; }
ok()  { c_green "✓"; printf ' %s\n' "$*"; }

build_scanner() {
    say "compilation du scanner Rust (cargo build --release)..."
    ( cd "$NX_HOME/scanner" && cargo build --release ) || {
        c_red "cargo build a échoué"; echo; exit 1;
    }
    [[ -x "$SCAN_BIN" ]] || { c_red "binaire nexus_scan introuvable"; echo; exit 1; }
    ok "scanner prêt : $SCAN_BIN"
}

case "${1:-help}" in
    build)
        build_scanner
        ;;
    *)
        if [[ ! -x "$SCAN_BIN" ]]; then
            say "scanner absent — compilation automatique..."
            build_scanner
        fi
        exec python3 "$NX_HOME/nexus_core.py" "$@"
        ;;
esac
