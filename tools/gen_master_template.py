#!/usr/bin/env python3
"""
gen_master_template.py -- regenerate EldenRing-MASTER-template.yaml from the apworld's options.py.

Parses worlds/eldenring/options.py with `ast` (no imports of AP), reads the EROptions dataclass field
order, and emits one commented line per option at its DEFAULT, with valid values + the first line of
its docstring -- exactly the format the template was originally hand-generated in. Keeps everything in
sync automatically; re-run whenever options.py changes.

  python tools/gen_master_template.py
Writes ../EldenRing-MASTER-template.yaml (LF). Run on Windows (the sandbox mount truncates large reads).
"""
import ast, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
# tools/ lives in the repo root; options.py is under Archipelago/worlds/eldenring
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "tools" else HERE
OPTIONS = os.path.join(ROOT, "Archipelago", "worlds", "eldenring", "options.py")
OUT = os.path.join(ROOT, "EldenRing-MASTER-template.yaml")

KNOWN_BASES = {"Choice", "TextChoice", "Toggle", "DefaultOnToggle",
               "Range", "NamedRange", "OptionSet", "ItemSet", "LocationSet", "FreeText"}


def first_doc_line(node):
    d = ast.get_docstring(node)
    if not d:
        return ""
    for ln in d.splitlines():
        ln = ln.strip()
        if ln:
            return ln
    return ""


def main():
    src = open(OPTIONS, "r", encoding="utf-8").read()
    tree = ast.parse(src)

    classes = {c.name: c for c in tree.body if isinstance(c, ast.ClassDef)}

    def kind_of(name, seen=None):
        seen = seen or set()
        c = classes.get(name)
        if not c:
            return None
        for b in c.bases:
            bn = b.id if isinstance(b, ast.Name) else (b.attr if isinstance(b, ast.Attribute) else None)
            if bn in KNOWN_BASES:
                return bn
            if bn in classes and bn not in seen:
                k = kind_of(bn, seen | {name})
                if k:
                    return k
        return None

    def consts(c):
        out = {}
        for n in c.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                try:
                    out[n.targets[0].id] = ast.literal_eval(n.value)
                except Exception:
                    pass
        return out

    def describe(cls_name):
        """-> (default_repr, valid_str, desc)"""
        c = classes.get(cls_name)
        if not c:
            return ("", "?", "")
        k = kind_of(cls_name)
        cv = consts(c)
        desc = first_doc_line(c)
        if k in ("Choice", "TextChoice"):
            opts = {v: n[len("option_"):] for n, v in cv.items() if n.startswith("option_")}
            valid = " / ".join(opts[v] for v in sorted(opts))
            dft = cv.get("default", min(opts) if opts else 0)
            return (opts.get(dft, str(dft)), valid, desc)
        if k == "DefaultOnToggle":
            return ("true", "false / true", desc)
        if k == "Toggle":
            return ("false", "false / true", desc)
        if k in ("Range", "NamedRange"):
            lo, hi, dft = cv.get("range_start", 0), cv.get("range_end", 0), cv.get("default", 0)
            extra = ""
            srn = cv.get("special_range_names")
            if isinstance(srn, dict) and srn:
                extra = " or " + " / ".join(srn.keys())
            return (str(dft), f"{lo}..{hi} (integer){extra}", desc)
        if k in ("OptionSet", "ItemSet", "LocationSet"):
            return ("", "list of names", desc)
        if k == "FreeText":
            return (str(cv.get("default", "")), "text", desc)
        return (str(cv.get("default", "")), k or "?", desc)

    ero = classes.get("EROptions")
    if not ero:
        raise SystemExit("[FAIL] EROptions class not found")
    fields = [(n.target.id, n.annotation.id)
              for n in ero.body
              if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
              and isinstance(n.annotation, ast.Name)]

    today = datetime.date.today().isoformat()
    L = []
    L.append("# ============================================================================")
    L.append("# ER ARCHIPELAGO -- MASTER OPTION TEMPLATE (all options, commented out).")
    L.append(f"# Auto-generated from worlds/eldenring/options.py {today} by tools/gen_master_template.py.")
    L.append("# Each line shows the option at its DEFAULT value; uncomment + edit the ones you want.")
    L.append("# Valid values and a one-line description follow each option on the same line.")
    L.append("# NOTE: accessibility + progression_balancing are AP-core (not ER) -- listed at the end.")
    L.append("# ============================================================================")
    L.append("")
    L.append("name: Player")
    L.append("description: ER Archipelago master template")
    L.append("game: EldenRing")
    L.append("")
    L.append("EldenRing:")
    for field, cls in fields:
        dft, valid, desc = describe(cls)
        left = f"  # {field}: {dft}".rstrip()
        pad = max(1, 38 - len(left))
        L.append(f"{left}{' ' * pad}# [{valid}] {desc}".rstrip())
    L.append("")
    L.append("  # ---- AP-core options ----")
    L.append("  # accessibility: full          # full / minimal / none")
    L.append("  # progression_balancing: 50    # 0..99 (default 50)")
    L.append("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))
    print(f"[ok] wrote {OUT}  ({len(fields)} ER options)")


if __name__ == "__main__":
    main()
