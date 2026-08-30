import collections

import pytest

import datamine_flag_names as subject


def complete_stats():
    return collections.Counter(
        files=subject.MIN_EVENT_FILES,
        events=subject.MIN_EVENTS,
    )


def complete_rows():
    return [object()] * subject.MIN_LABELLED_FLAGS


@pytest.mark.parametrize(
    ("field", "short_by", "message"),
    [
        ("files", 1, "event files=588"),
        ("events", 1, "events=4892"),
    ],
)
def test_incomplete_event_corpus_is_unknown_not_an_empty_answer(field, short_by, message):
    stats = complete_stats()
    stats[field] -= short_by
    with pytest.raises(SystemExit, match=message):
        subject.validate_complete(complete_rows(), stats)


def test_label_shrink_refuses_even_when_event_counts_are_complete():
    with pytest.raises(SystemExit, match="labelled flags=5110"):
        subject.validate_complete(complete_rows()[:-1], complete_stats())


def test_measured_complete_corpus_passes_at_the_exact_floor():
    subject.validate_complete(complete_rows(), complete_stats())
