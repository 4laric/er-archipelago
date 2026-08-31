"""#220: shared shop ranges must not turn an NPC-owned release into every opener's stock."""
import importlib.util
import os
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "datamine_merchant_shops", os.path.join(HERE, "datamine_merchant_shops.py"))
merchant_shops = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merchant_shops)


class ReleaseOwnerFilterTests(unittest.TestCase):
    def test_named_owner_accepts_its_talk_family_and_twin_maiden_resell(self):
        self.assertTrue(merchant_shops._release_owner_accepts_talk(309001600, "309"))
        self.assertTrue(merchant_shops._release_owner_accepts_talk(309003100, "309"))
        self.assertTrue(merchant_shops._release_owner_accepts_talk(600001110, "309"))

    def test_named_owner_rejects_an_unrelated_shared_range_opener(self):
        self.assertFalse(merchant_shops._release_owner_accepts_talk(419002200, "309"))
        self.assertFalse(merchant_shops._release_owner_accepts_talk(302001000, "309"))

    def test_build_filters_only_rows_with_authored_owner_evidence(self):
        shop_ids = {100117, 100122}
        talk_data = {
            309001600: {"ranges": {(100100, 100124)}, "binder_maps": set()},
            419002200: {"ranges": {(100100, 100124)}, "binder_maps": set()},
        }
        talk_maps = {309001600: {"m16_00"}, 419002200: {"m22_00"}}
        rows = merchant_shops.build(
            shop_ids, talk_data, talk_maps, {}, {}, release_owners={100117: "309"})

        self.assertEqual({row[0] for row in rows[100117]}, {309001600})
        self.assertEqual({row[0] for row in rows[100122]}, {309001600, 419002200})

    def test_refine_mode_is_idempotent(self):
        merchant_shops.load_release_owners = lambda: {100117: "309"}
        source = ("row_id\ttalk_id\tnpc_param_id\tmerchant_name\tmap_id\tmap_source\n"
                  "100117\t309001600\t1\tPatches\tm16_00\tmsb\n"
                  "100117\t419002200\t2\tThiollier\tm22_00\tmsb\n"
                  "100122\t419002200\t2\tThiollier\tm22_00\tmsb\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "merchant_shops.tsv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(source)
            merchant_shops.refine_release_owners(path)
            with open(path, encoding="utf-8") as fh:
                once = fh.read()
            merchant_shops.refine_release_owners(path)
            with open(path, encoding="utf-8") as fh:
                twice = fh.read()

        self.assertEqual(once, twice)
        self.assertIn("100117\t309001600", once)
        self.assertNotIn("100117\t419002200", once)
        self.assertIn("100122\t419002200", once)


if __name__ == "__main__":
    unittest.main()
