"""TrapLink's option/slot-data/handshake contract."""

import unittest

from .. import contract
from ..features import traplink


class _Opt:
    def __init__(self, value):
        self.value = value


class _World:
    def __init__(self, enabled):
        class Options:
            pass
        self.options = Options()
        self.options.trap_link = _Opt(enabled)


class TrapLinkContract(unittest.TestCase):
    def test_off_is_inert_and_on_requires_the_client_feature(self):
        feature = traplink.TrapLinkFeature()
        self.assertEqual(feature.slot_data(_World(False)), {})
        self.assertEqual(
            feature.slot_data(_World(True)),
            {contract.REQUIRES_CLIENT_FEATURES: [traplink.CLIENT_FEATURE_TAG]},
        )

    def test_option_is_off_by_default(self):
        self.assertEqual(traplink.TrapLink.default, 0)

    def test_options_contract_declares_the_wire_key(self):
        keys = {key.name for key in contract.OPTIONS_SUBKEYS}
        self.assertIn("trap_link", keys)


if __name__ == "__main__":
    unittest.main()
