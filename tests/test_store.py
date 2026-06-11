from vts.artifacts.schemas import MacroSnapshot, MarketStance
from datetime import date


def test_save_and_load(store, sample_snapshot):
    store.save(sample_snapshot, "snapshots", "2026-06-09")
    loaded = store.load("snapshots", "2026-06-09", MacroSnapshot)
    assert loaded.stance == MarketStance.CAUTIOUS
    assert loaded.date == date(2026, 6, 9)
    assert loaded.treasury_10y == 4.28


def test_list_ids_sorted(store, sample_snapshot):
    store.save(sample_snapshot, "snapshots", "2026-06-09")
    store.save(sample_snapshot, "snapshots", "2026-06-08")
    ids = store.list_ids("snapshots")
    assert ids == ["2026-06-08", "2026-06-09"]


def test_list_ids_empty(store):
    assert store.list_ids("nonexistent") == []


def test_latest(store, sample_snapshot):
    s1 = sample_snapshot.model_copy(update={"date": date(2026, 6, 8)})
    store.save(s1, "snapshots", "2026-06-08")
    store.save(sample_snapshot, "snapshots", "2026-06-09")
    latest = store.latest("snapshots", MacroSnapshot)
    assert latest.date == date(2026, 6, 9)


def test_latest_empty(store):
    assert store.latest("snapshots", MacroSnapshot) is None


def test_to_markdown(store, sample_snapshot):
    md = store.to_markdown(sample_snapshot)
    assert "4.28" in md
    assert "18.5" in md


def test_load_nonexistent_raises(store):
    import pytest
    with pytest.raises(FileNotFoundError):
        store.load("snapshots", "nonexistent", MacroSnapshot)
