"""Recovery of a dead firer must not steal the newer live firer's claim (#152296)."""
from contextlib import asynccontextmanager
import json

from cron import executions, jobs, scheduler_authority


def test_dead_firer_receipt_defers_for_newer_live_run_then_books_history(tmp_path, monkeypatch):
    with jobs.use_cron_store(tmp_path / 'cron'):
        job = jobs.create_job(prompt='report', schedule='every 1h', deliver='local')
        a = executions.create_execution(job['id'], source='direct')['id']
        executions.mark_execution_running(a)
        with executions._transaction() as conn:
            conn.execute(
                'UPDATE executions SET process_id=?, pid=? WHERE id=?',
                ('dead-firer', 999999, a))
        frozen_a = jobs.get_job(job['id'])
        params = {'job_id': job['id'], 'request_id': a, 'extra_prompt': None}
        journal = scheduler_authority.journal_path(job['id'], a)
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(json.dumps({'params': params, 'receipt': {'admission_id': 'a'}}))

        claimed_b = jobs.claim_job_for_fire(job['id'], force=True, return_job=True)
        assert claimed_b
        owner_b = claimed_b['fire_claim']['by']
        b = executions.create_execution(job['id'], source='direct')['id']
        executions.mark_execution_running(b)

        class Peer:
            async def rpc(self, method, **kwargs):
                assert method == 'cron.recover' and kwargs == params
                # The owner may return A's frozen snapshot rather than the current B job.
                return {'status': 'terminal', 'job': frozen_a,
                        'result': [True, 'report', 'answer A', None]}

        @asynccontextmanager
        async def connect():
            yield Peer()

        monkeypatch.setattr('hermes_cli.gateway_client.connect_gateway', connect)
        for _ in range(2):
            scheduler_authority.reconcile_pending()
            assert journal.exists()
            assert executions.get_execution(a)['status'] == 'running'
            assert jobs.heartbeat_fire_claim(job['id'], expected_owner=owner_b)
            assert not list(jobs._job_output_dir(job['id']).glob('*.md'))

        assert jobs.mark_job_run(job['id'], True, expected_fire_owner=owner_b,
                                 execution_id=b)
        assert executions.finish_execution(b, success=True) is not None
        b_latest = jobs.get_job(job['id'])

        scheduler_authority.reconcile_pending()
        assert executions.get_execution(a)['status'] == 'completed'
        assert not journal.exists()
        assert jobs.get_job(job['id']) == b_latest
        assert not list(jobs._job_output_dir(job['id']).glob('*.md'))
