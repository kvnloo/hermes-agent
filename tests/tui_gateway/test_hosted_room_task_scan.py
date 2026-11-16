"""A room task scan reads the driver store once and keeps the per-status order."""

from types import SimpleNamespace

from gateway import hosted_room_driver as driver
from gateway import hosted_rooms
from tui_gateway import hosted_room_service
from tui_gateway.hosted_room_service import HostedRoomService


def service(tmp_path):
    db = tmp_path / "state.db"
    hosted_rooms.create_room(
        db, room_id="one", name="one",
        members=[{"member_id": "writer", "profile": "writer", "handle": "writer"}],
        authority_gateway_id="gateway",
    )
    return HostedRoomService(SimpleNamespace(), db_path=db)


def test_terminal_scan_opens_the_driver_store_once(tmp_path, monkeypatch):
    instance = service(tmp_path)
    original, calls = hosted_room_service.driver.list_tasks, []

    def counted(*args, **kwargs):
        calls.append(kwargs.get("statuses"))
        return original(*args, **kwargs)

    monkeypatch.setattr(hosted_room_service.driver, "list_tasks", counted)
    assert list(instance._list_tasks("one", hosted_room_service._TERMINAL_STATUSES)) == []
    assert calls == [hosted_room_service._TERMINAL_STATUSES]


def test_scan_groups_by_requested_status_in_admission_order(tmp_path, monkeypatch):
    instance = service(tmp_path)
    admitted = [{"id": "a", "status": "settled"}, {"id": "b", "status": "failed"},
                {"id": "c", "status": "running"}, {"id": "d", "status": "settled"}]
    monkeypatch.setattr(hosted_room_service.driver, "list_tasks", lambda *args, **kwargs: admitted)
    scanned = [task["id"] for task in instance._list_tasks("one", ("failed", "settled"))]
    assert scanned == ["b", "a", "d"]

def test_live_scan_reads_once_without_decoding_retained_terminal_tasks(tmp_path, monkeypatch):
    instance = service(tmp_path)
    for task_id, seq in (("retained", 1), ("active", 2)):
        driver.admit_task(
            instance.db_path,
            driver.TaskIdentity("one", task_id, f"thread-{task_id}", f"turn-{task_id}"),
            payload={"target_profile": "writer", "prompt": task_id, "source_event_seq": seq},
            clock=lambda: 10.0,
        )
    driver.cancel_task(
        instance.db_path,
        driver.TaskIdentity("one", "retained", "thread-retained", "turn-retained"),
        cancel_id="cancel-retained", expected_cancel_generation=0, clock=lambda: 11.0,
    )

    decoded, connections = [], []
    original_decode, original_connect = driver._task_from_row, driver._connect

    def decode(row, **kwargs):
        decoded.append(row["task_id"])
        return original_decode(row, **kwargs)

    def connect(db_path):
        connections.append(db_path)
        return original_connect(db_path)

    monkeypatch.setattr(driver, "_task_from_row", decode)
    monkeypatch.setattr(driver, "_connect", connect)

    scanned = list(instance._list_tasks("one", hosted_room_service._LIVE_STATUSES))
    assert [task["identity"].task_id for task in scanned] == ["active"]
    assert connections == [instance.db_path]
    assert decoded == ["active"]
