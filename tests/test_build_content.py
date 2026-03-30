from pathlib import Path


def test_sync_packaged_content_tree_copies_source_json_and_removes_stale_files(tmp_path: Path) -> None:
    from slay_the_spire.build_content import sync_packaged_content_tree

    source_root = tmp_path / "content"
    target_root = tmp_path / "src" / "slay_the_spire" / "data" / "content"

    (source_root / "cards").mkdir(parents=True)
    (source_root / "cards" / "starter.json").write_text('{"cards": []}', encoding="utf-8")

    (target_root / "cards").mkdir(parents=True)
    (target_root / "cards" / "stale.json").write_text('{"cards": [{"id": "stale"}]}', encoding="utf-8")

    sync_packaged_content_tree(source_root=source_root, target_root=target_root)

    assert (target_root / "cards" / "starter.json").read_text(encoding="utf-8") == '{"cards": []}'
    assert not (target_root / "cards" / "stale.json").exists()
