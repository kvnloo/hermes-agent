"""Regression for operator-disabled skills in Kanban swarm stage cards.

The real managed-worker gate in gateway/session_kanban.py rejects a task
before the model turn when preloading yields missing skills and no loaded skills.
"""

from agent import skill_commands
from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli.kanban_swarm import SwarmWorkerSpec, create_swarm


def test_swarm_disabled_stage_skills_do_not_abort_before_model(tmp_path, monkeypatch):
    # The bundled skills are installed, but explicitly disabled by the operator.
    # Stub only their catalog lookup so this exercises the real preload filter
    # and the same missing/loaded decision used by the managed-worker gate.
    disabled = {"requesting-code-review", "humanizer"}
    monkeypatch.setattr(skill_commands, "_disabled_skill_names", lambda: disabled)
    monkeypatch.setattr(
        skill_commands,
        "_load_skill_payload",
        lambda identifier, task_id=None: ({"name": identifier}, None, identifier),
    )

    conn = kbc.connect(tmp_path / "kanban.db")
    try:
        created = create_swarm(
            conn,
            goal="Compare worker findings and deliver a synthesis.",
            workers=[SwarmWorkerSpec(profile="analyst", title="Investigate", body="Find evidence")],
            verifier_assignee="reviewer",
            synthesizer_assignee="writer",
        )

        for task_id in (created.verifier_id, created.synthesizer_id):
            stage = kb.get_task(conn, task_id)
            assert stage is not None
            assert created.root_id in stage.body  # Native role instructions still apply.
            _prompt, loaded, missing = skill_commands.build_preloaded_skills_prompt(
                stage.skills or [], task_id=task_id
            )
            assert not (missing and not loaded), (
                f"{stage.title} would raise kanban_skills_unavailable before its model turn: {missing}"
            )
    finally:
        conn.close()
