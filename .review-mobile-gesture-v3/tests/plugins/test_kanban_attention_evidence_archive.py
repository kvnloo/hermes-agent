import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest


PACKET_ROOT = Path("plugins/kanban/evidence/attention-responsive")
PACKETS = {
    "electron-e2e-v2": 26,
    "webui-e2e": 11,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_packet(packet: Path, expected_payloads: int) -> None:
    manifest_path = packet / "manifest.json"
    receipt_path = packet / "manifest.receipt.json"
    manifest = json.loads(manifest_path.read_text())
    receipt = json.loads(receipt_path.read_text())

    assert len(manifest["payloads"]) == expected_payloads
    assert receipt["artifact"] == "manifest.json"
    assert receipt["payloadCount"] == expected_payloads
    assert receipt["bytes"] == manifest_path.stat().st_size
    assert receipt["sha256"] == _sha256(manifest_path)

    for payload in manifest["payloads"]:
        payload_path = packet / payload["path"]
        assert payload_path.is_file(), payload["path"]
        assert payload_path.stat().st_size == payload["bytes"]
        assert _sha256(payload_path) == payload["sha256"]


def test_sealed_attention_packets_survive_clean_git_archive(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    archive = tmp_path / "repository.tar"
    with archive.open("wb") as stream:
        subprocess.run(
            ["git", "archive", "--format=tar", "HEAD"],
            cwd=repo,
            stdout=stream,
            check=True,
        )
    export = tmp_path / "export"
    export.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(export, filter="data")

    for packet_name, expected_payloads in PACKETS.items():
        _verify_packet(export / PACKET_ROOT / packet_name, expected_payloads)


def test_packet_verifier_fails_when_manifest_payload_is_omitted(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    source = repo / PACKET_ROOT / "electron-e2e-v2"
    packet = tmp_path / "electron-e2e-v2"
    shutil.copytree(source, packet)
    manifest = json.loads((packet / "manifest.json").read_text())
    (packet / manifest["payloads"][0]["path"]).unlink()

    with pytest.raises(AssertionError):
        _verify_packet(packet, PACKETS["electron-e2e-v2"])
