import json
import time

from thread_manager import MatchThreads, ThreadManager


def test_missing_file_starts_empty(tmp_path):
    manager = ThreadManager(str(tmp_path / "threads.json"))
    assert manager.threads == {}
    assert manager.get_threads("MLS-MAT-0009MQ") is None


async def test_round_trip(tmp_path):
    path = tmp_path / "threads.json"
    manager = ThreadManager(str(path))
    await manager.add_threads(
        "MLS-MAT-0009MQ",
        MatchThreads(slug="stl-vs-la-10-11-2026", pre="abc", stream_link="def", created=1000.0),
    )
    await manager.update_thread("MLS-MAT-0009MQ", match="ghi", post="jkl")

    on_disk = json.loads(path.read_text())
    assert on_disk == {
        "MLS-MAT-0009MQ": {
            "slug": "stl-vs-la-10-11-2026",
            "pre": "abc",
            "match": "ghi",
            "post": "jkl",
            "stream-link": "def",
            "created": 1000.0,
        }
    }

    reloaded = ThreadManager(str(path)).get_threads("MLS-MAT-0009MQ")
    assert reloaded == MatchThreads(
        slug="stl-vs-la-10-11-2026", match="ghi", pre="abc", post="jkl", stream_link="def",
        created=1000.0,
    )


async def test_unset_fields_are_omitted(tmp_path):
    path = tmp_path / "threads.json"
    manager = ThreadManager(str(path))
    await manager.add_threads("MLS-MAT-0009N5", MatchThreads(slug="stl-vs-van", created=1000.0))
    assert json.loads(path.read_text()) == {"MLS-MAT-0009N5": {"slug": "stl-vs-van", "created": 1000.0}}


async def test_update_unknown_match_is_noop(tmp_path):
    path = tmp_path / "threads.json"
    manager = ThreadManager(str(path))
    await manager.update_thread("MLS-MAT-0009N5", match="abc")
    assert manager.threads == {}
    assert not path.exists()


async def test_save_leaves_no_temp_files(tmp_path):
    manager = ThreadManager(str(tmp_path / "threads.json"))
    for i in range(3):
        await manager.add_threads(f"MLS-MAT-{i}", MatchThreads(slug=str(i)))
    assert [p.name for p in tmp_path.iterdir()] == ["threads.json"]


async def test_add_threads_stamps_created(tmp_path):
    manager = ThreadManager(str(tmp_path / "threads.json"))
    before = time.time()
    await manager.add_threads("MLS-MAT-0009N5", MatchThreads(slug="stl-vs-van"))
    created = manager.get_threads("MLS-MAT-0009N5").created
    assert before <= created <= time.time()

    # Updating an entry keeps its original timestamp
    await manager.add_threads("MLS-MAT-0009N5", manager.get_threads("MLS-MAT-0009N5"))
    assert manager.get_threads("MLS-MAT-0009N5").created == created


async def test_prune(tmp_path):
    path = tmp_path / "threads.json"
    day = 86400
    path.write_text(json.dumps({
        "old": {"slug": "old", "match": "a", "created": time.time() - 40 * day},
        "recent": {"slug": "recent", "match": "b", "created": time.time() - 5 * day},
        "legacy": {"slug": "legacy", "match": "c"},
    }))
    manager = ThreadManager(str(path))
    assert await manager.prune(30) == 1

    assert set(manager.threads) == {"recent", "legacy"}
    on_disk = json.loads(path.read_text())
    assert set(on_disk) == {"recent", "legacy"}
    # Entries saved before timestamps existed get one now
    assert on_disk["legacy"]["created"] >= time.time() - 60


async def test_prune_nothing_to_do_does_not_write(tmp_path):
    path = tmp_path / "threads.json"
    manager = ThreadManager(str(path))
    assert await manager.prune(30) == 0
    assert not path.exists()
