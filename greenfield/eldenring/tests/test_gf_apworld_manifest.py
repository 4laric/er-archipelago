"""THE APWORLD MANIFEST MUST NAME THE GAME THE WORLD ACTUALLY REGISTERS.

AP 0.6.7 `worlds/__init__.py` reads `archipelago.json` from INSIDE the apworld:

    if file.endswith("archipelago.json"):
        manifest = json.load(manifest_file)
    game = manifest.get("game")
    if game in AutoWorldRegister.world_types:
        AutoWorldRegister.world_types[game].world_version = ...

and, for a packaged .apworld, `load_apworlds()` -> `APWorldContainer.read()`:

    except InvalidDataError as e:
        if version_tuple < (0, 7, 0):
            logging.error("Invalid or missing manifest file ... "
                          "This apworld will stop working with Archipelago 0.7.0.")
        else:
            raise e                      # <-- 0.7.0: the apworld does NOT LOAD

TWO defects this guards, both live before 2026-07-12 and neither caught by anything:

  1. The manifest lived at the REPO ROOT, and build.ps1 zips `greenfield\\eldenring` ONLY -- so the
     shipped .apworld contained NO manifest. Every player got the error above on load, and the world
     would have hard-failed on AP 0.7.0.

  2. The manifest said `"game": "EldenRing"` while the world registers as `GAME = "Elden Ring"`. The
     `game in world_types` lookup is guarded, so this failed SILENTLY: world_version simply never got
     set. Packaging the manifest without fixing the name would have traded a loud bug for a quiet one.

Exact same class as the shipping-yaml bug (2406c20, "the shipped yaml named a game that does not
exist"). It was one file over, and nothing pointed at it. This test points at it.
"""
import json
import os
import unittest

from ..core import GAME

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(HERE, "archipelago.json")


class TestApworldManifest(unittest.TestCase):

    def test_manifest_ships_inside_the_package(self):
        """It must sit BESIDE __init__.py, or build.ps1's zip of greenfield\\eldenring omits it."""
        self.assertTrue(
            os.path.isfile(MANIFEST),
            "archipelago.json is not in the world package -- the packaged .apworld will have NO "
            "manifest, which AP 0.6.x logs as an error and AP 0.7.0 REFUSES TO LOAD. It must live "
            "beside __init__.py, not at the repo root (build.ps1 only zips greenfield\\eldenring).")

    def test_manifest_game_is_the_game_the_world_registers(self):
        """`game` must equal World.game, or AP's `game in world_types` lookup silently misses."""
        with open(MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
        self.assertEqual(
            manifest.get("game"), GAME,
            f"manifest game {manifest.get('game')!r} != world GAME {GAME!r}. AP looks the manifest's "
            f"game up in AutoWorldRegister.world_types; the lookup is GUARDED, so a mismatch does not "
            f"raise -- world_version just never gets set and nobody notices.")

    def test_manifest_declares_the_fields_ap_reads(self):
        with open(MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
        for key in ("game", "world_version", "minimum_ap_version"):
            self.assertIn(key, manifest, f"manifest is missing {key!r}, which AP reads")
        self.assertRegex(str(manifest["world_version"]), r"^\d+\.\d+\.\d+$",
                         "world_version must be tuplize_version-able (X.Y.Z)")

    def test_the_three_version_numbers_are_one_number(self):
        """archipelago.json, contract.py, and the client crate must all say the same thing.

        They did not: the client sat at 0.1.0-beta.4 against apworld 0.2.0 for months. The semver
        BAND gate that used to force them together was retired 2026-07-11 (`versions` became a
        descriptive string and the handshake compares the CONTRACT HASH), and nothing replaced the
        pressure -- so the number stopped moving and its comment went on describing a dead mechanism.

        Nothing in production reads these, so this protects the BUG REPORT rather than a behaviour:
        `versions` is the string every report carries, and three disagreeing numbers make triage
        guesswork. The client half is asserted in core.rs
        (client_version_matches_the_apworld_it_was_built_against) against the generated
        contract_gen.rs, which closes the loop.
        """
        import json as _json
        import os as _os
        from .. import contract as _contract
        here = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        with open(_os.path.join(here, "archipelago.json"), encoding="utf-8") as fh:
            manifest = _json.load(fh)
        self.assertEqual(
            str(manifest["world_version"]), _contract.APWORLD_VERSION,
            "archipelago.json world_version and contract.APWORLD_VERSION disagree -- the apworld "
            "would announce one version to Archipelago and a different one to the client.")
