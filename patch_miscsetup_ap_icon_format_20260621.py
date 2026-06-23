#!/usr/bin/env python3
"""
Patch MiscSetup.InjectApItemIcon so the telescope->flower swap sets the TPF texture
Format byte to match the SUPPLIED flower DDS when that DDS is UNCOMPRESSED.

Why: SoulsFormats writes the Format byte verbatim on PC and only re-derives Type/Mipmaps
from the DDS header (TPF.cs WriteHeader). The old code kept the vanilla telescope's Format
byte (BC7) while swapping in flower pixel bytes -- so the flower DDS HAD to be hand-encoded
to the exact vanilla BC7 format (the never-completed texconv step). With this patch we ship an
uncompressed B8G8R8A8 flower DDS (diste/Archipelago/ap_telescope_icon.dds) and the bake sets
Format=9 to match it, so no texconv / format-matching is needed. A format-matched (BC7) flower
still works -- compressed DDS keep the vanilla byte.

Idempotent. CRLF + UTF-8-BOM preserving. Run on Windows from repo root:  python patch_miscsetup_ap_icon_format_20260621.py
"""
import io, sys, os

PATH = os.path.join("SoulsRandomizers", "RandomizerCommon", "MiscSetup.cs")

OLD_SWAP = (
    "            // Keep the existing Format/Flags1 byte; SoulsFormats re-derives Type/Mipmaps from the\r\n"
    "            // new DDS for PC textures on write.\r\n"
    "            tpf.Textures[0].Bytes = File.ReadAllBytes(flowerPath);\r\n"
    "            entry.Bytes = tpf.Write();\r\n"
)

NEW_SWAP = (
    "            // Swap in the flower DDS. SoulsFormats re-derives Type/Mipmaps from the new DDS on\r\n"
    "            // write (PC) but does NOT change the Format byte. If the flower DDS is a different\r\n"
    "            // pixel format than the vanilla telescope (e.g. uncompressed B8G8R8A8 vs vanilla BC7)\r\n"
    "            // the format byte must be updated to match or the game renders garbage. Detect an\r\n"
    "            // uncompressed DDS and set the matching ER format byte; a format-matched (BC7) flower\r\n"
    "            // keeps the vanilla byte.\r\n"
    "            byte[] flowerBytes = File.ReadAllBytes(flowerPath);\r\n"
    "            byte? uncompressedFormat = TryGetUncompressedErFormat(flowerBytes);\r\n"
    "            if (uncompressedFormat.HasValue)\r\n"
    "                tpf.Textures[0].Format = uncompressedFormat.Value;\r\n"
    "            tpf.Textures[0].Bytes = flowerBytes;\r\n"
    "            entry.Bytes = tpf.Write();\r\n"
)

ANCHOR = (
    "            Console.WriteLine($\"AP icon: swapped telescope icon ({prefix}{iconId}) for the Archipelago flower -> {outPath}\");\r\n"
    "        }\r\n"
)

HELPER = (
    "\r\n"
    "        /// <summary>\r\n"
    "        /// If <paramref name=\"ddsBytes\"/> is an UNCOMPRESSED DDS, returns the matching ER TPF\r\n"
    "        /// format byte so the icon swap can update the texture's Format to match. Returns null\r\n"
    "        /// for compressed/DX10 DDS (those keep the vanilla telescope's format byte, assumed to\r\n"
    "        /// already match a format-matched flower).\r\n"
    "        /// </summary>\r\n"
    "        private static byte? TryGetUncompressedErFormat(byte[] ddsBytes)\r\n"
    "        {\r\n"
    "            try\r\n"
    "            {\r\n"
    "                DDS dds = new DDS(ddsBytes);\r\n"
    "                string fourCC = (dds.ddspf.dwFourCC ?? \"\").Replace(\"\\0\", \"\").Trim();\r\n"
    "                if (fourCC.Length > 0) return null;\r\n"
    "                switch (dds.ddspf.dwRGBBitCount)\r\n"
    "                {\r\n"
    "                    case 32: return 9;  // B8G8R8A8\r\n"
    "                    case 16: return 6;  // B5G5R5A1_UNORM\r\n"
    "                    case 8: return 16;  // A8\r\n"
    "                    default: return null;\r\n"
    "                }\r\n"
    "            }\r\n"
    "            catch { return null; }\r\n"
    "        }\r\n"
)

def main():
    if not os.path.exists(PATH):
        print(f"ERROR: {PATH} not found (run from repo root)"); sys.exit(1)
    with io.open(PATH, "r", encoding="utf-8-sig", newline="") as f:
        src = f.read()

    if "TryGetUncompressedErFormat" in src:
        print("Already patched (TryGetUncompressedErFormat present); no change."); return

    if OLD_SWAP not in src:
        print("ERROR: swap block anchor not found; aborting (file drifted)."); sys.exit(2)
    if ANCHOR not in src:
        print("ERROR: method-close anchor not found; aborting."); sys.exit(2)

    src = src.replace(OLD_SWAP, NEW_SWAP, 1)
    src = src.replace(ANCHOR, ANCHOR + HELPER, 1)

    with io.open(PATH, "w", encoding="utf-8-sig", newline="") as f:
        f.write(src)
    print("Patched MiscSetup.cs: format-aware AP icon swap + TryGetUncompressedErFormat helper.")

if __name__ == "__main__":
    main()
