"""#1077 -- five short-flag lots have no world or scripted acquisition route."""

from ..data import LOCATIONS, NOT_RANDOMIZED


FLAGS = {540504, 540614, 540616, 540632, 540650}


def test_worldless_shaded_castle_rows_are_not_checks():
    emitted = {int(flag) for rows in LOCATIONS.values() for _name, _ap, flag in rows}
    assert FLAGS.isdisjoint(emitted)


def test_worldless_shaded_castle_rows_have_an_explicit_disposition():
    for flag in FLAGS:
        assert "worldless_short_lot" in NOT_RANDOMIZED[flag]
