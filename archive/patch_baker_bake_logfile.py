#!/usr/bin/env python3
"""
patch_baker_bake_logfile.py -- persist the FULL bake output to a timestamped log file.

Today the bake only Console.WriteLine's (visible in a console, lost otherwise) + writes per-feature
ap_*_<stamp> diag files; there is no single full log. This tees Console.Out/Error to
ap_bake_<stamp>.log (same Util.ApDiagPath dir/stamp convention) at the very start of
RandomizeForArchipelago, capturing EVERYTHING -- RegionFogGates lines, the CompletionScaling diag,
every ap_* echo, AND the '=== RandomizeForArchipelago FAILED ===' stack (printed later in
submit_Click's catch). Installed once; intentionally NOT restored so the failure handler is captured.

ArchipelagoForm.cs (LF). Idempotent. Run on Windows; rebuild SoulsRandomizers.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
AF = os.path.join(ROOT, "SoulsRandomizers", "RandomizerCommon", "ArchipelagoForm.cs")


def _lf(t):
    return t.encode("utf-8")


HELPER_ANCHOR = _lf("        private void RandomizeForArchipelago(ArchipelagoSession session, Dictionary<string, object> slotData)\n")
HELPER = _lf('''\
        // Full-bake log (tee): mirror Console.Out/Error to a timestamped ap_bake_<stamp>.log so the
        // ENTIRE bake is persisted (RegionFogGates, CompletionScaling diag, ap_* echoes, and the
        // FAILED stack from submit_Click's catch). Installed once at bake start; deliberately NOT
        // restored, so output that happens after RandomizeForArchipelago unwinds is still captured.
        private sealed class TeeTextWriter : System.IO.TextWriter
        {
            private readonly System.IO.TextWriter _a, _b;
            public TeeTextWriter(System.IO.TextWriter a, System.IO.TextWriter b) { _a = a; _b = b; }
            public override System.Text.Encoding Encoding => _a.Encoding;
            public override void Write(char c) { _a.Write(c); _b.Write(c); }
            public override void Write(string s) { _a.Write(s); _b.Write(s); }
            public override void Flush() { _a.Flush(); _b.Flush(); }
        }
        private static System.IO.TextWriter _bakeRealOut, _bakeRealErr;
        private static System.IO.StreamWriter _bakeLogWriter;
        private static string StartBakeLog()
        {
            try
            {
                if (_bakeRealOut == null) { _bakeRealOut = Console.Out; _bakeRealErr = Console.Error; }
                try { _bakeLogWriter?.Flush(); _bakeLogWriter?.Dispose(); } catch { }
                string path = Util.ApDiagPath("ap_bake").Replace(".txt", ".log");
                _bakeLogWriter = new System.IO.StreamWriter(path, false) { AutoFlush = true };
                _bakeLogWriter.WriteLine($"=== ER AP bake log {DateTime.Now:yyyy-MM-dd HH:mm:ss} ===");
                Console.SetOut(new TeeTextWriter(_bakeRealOut, _bakeLogWriter));
                Console.SetError(new TeeTextWriter(_bakeRealErr, _bakeLogWriter));
                return path;
            }
            catch (Exception e) { try { Console.WriteLine("StartBakeLog failed: " + e.Message); } catch { } return null; }
        }
''')

CALL_ANCHOR = _lf('            SetStatusText("Downloading item data...");\n')
CALL = _lf('            string bakeLogPath = StartBakeLog(); Console.WriteLine($"Bake log -> {bakeLogPath}");\n')


def main():
    if not os.path.isfile(AF):
        raise SystemExit(f"[FAIL] not found: {AF}")
    with open(AF, "rb") as f:
        data = f.read()
    if b"StartBakeLog" in data:
        print("[skip] already patched.")
        return
    for a, lbl in ((HELPER_ANCHOR, "helper"), (CALL_ANCHOR, "call")):
        if data.count(a) != 1:
            raise SystemExit(f"[FAIL] {lbl} anchor x{data.count(a)} (want 1). No write.")
    data = data.replace(HELPER_ANCHOR, HELPER + HELPER_ANCHOR, 1)
    data = data.replace(CALL_ANCHOR, CALL_ANCHOR + CALL, 1)
    with open(AF, "wb") as f:
        f.write(data)
    print("[ok] full-bake log tee added (ap_bake_<stamp>.log). Rebuild SoulsRandomizers.")


if __name__ == "__main__":
    main()
