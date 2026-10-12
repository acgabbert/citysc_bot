import json

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
        MatchThreads(slug="stl-vs-la-10-11-2026", pre="abc", stream_link="def"),
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
        }
    }

    reloaded = ThreadManager(str(path)).get_threads("MLS-MAT-0009MQ")
    assert reloaded == MatchThreads(
        slug="stl-vs-la-10-11-2026", match="ghi", pre="abc", post="jkl", stream_link="def"
    )


async def test_unset_fields_are_omitted(tmp_path):
    path = tmp_path / "threads.json"
    manager = ThreadManager(str(path))
    await manager.add_threads("MLS-MAT-0009N5", MatchThreads(slug="stl-vs-van"))
    assert json.loads(path.read_text()) == {"MLS-MAT-0009N5": {"slug": "stl-vs-van"}}


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
