#!/usr/bin/env python3
"""Fix the stale CompletionScaling docstring in worlds/eldenring/options.py.

It said "REQUIRES enemy_rando on", but a scale-only bake pass now applies completion
scaling with enemy rando OFF too (confirmed 2026-06-22). Text-only -- no option logic,
dataclass, or default changes; gen behaviour is identical.

Safe by the ER patch conventions: byte-level, CRLF-preserving, idempotent (re-runnable),
py_compiles the result before touching disk, writes a .bak_csdoc backup. Run on Windows:
    python patch_apworld_completion_scaling_docstring.py
then  .\build.ps1 -Apworld   (repackage)  and a gen to pick it up.
"""
import os, sys, py_compile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "Archipelago", "worlds", "eldenring", "options.py")

OLD = "REQUIRES enemy_rando on."
NEW = ("Runs with OR without enemy_rando -- a scale-only bake pass applies it when "
       "enemy rando is off.")

def patch_text(text: str) -> str:
    if NEW in text:
        return text  # already patched
    n = text.count(OLD)
    if n != 1:
        raise SystemExit(f"ERROR: expected exactly 1 occurrence of {OLD!r}, found {n} "
                         f"-- aborting (file may have drifted; nothing written).")
    return text.replace(OLD, NEW, 1)

def main():
    if not os.path.isfile(TARGET):
        print("ERROR target not found:", TARGET); return 1
    raw = open(TARGET, "rb").read()
    total = raw.count(b"\n"); eol_crlf = raw.count(b"\r\n") == total and total > 0
    text = raw.decode("utf-8")
    work = text.replace("\r\n", "\n") if eol_crlf else text
    new_work = patch_text(work)
    if new_work == work:
        print("already patched -- no change."); return 0
    out = (new_work.replace("\n", "\r\n") if eol_crlf else new_work).encode("utf-8")
    with tempfile.NamedTemporaryFile("wb", suffix=".py", delete=False) as tf:
        tf.write(out); tmp = tf.name
    try:
        py_compile.compile(tmp, doraise=True)
    finally:
        os.remove(tmp)
    open(TARGET + ".bak_csdoc", "wb").write(raw)
    open(TARGET, "wb").write(out)
    print(f"patched CompletionScaling docstring ({'CRLF' if eol_crlf else 'LF'}); "
          f"backup -> options.py.bak_csdoc")
    return 0

if __name__ == "__main__":
    sys.exit(main())
