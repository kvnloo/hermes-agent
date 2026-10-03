"""Finite caller-lifecycle assessment: reconnect while old flagging is still blocked."""
import asyncio
from email.message import EmailMessage
import threading
import time

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.run import GatewayRunner
from plugins.platforms.email import adapter as email_adapter


class Connection:
    capabilities = ()

    def __init__(self, generation, state):
        self.generation, self.state = generation, state
        self.closed = False
        state['connections'].append(self)

    def login(self, *_):
        return 'OK', []

    def select(self, *_):
        return 'OK', []

    def logout(self):
        self.closed = True

    def uid(self, command, *args):
        self.state['calls'].append((self.generation, command, args))
        if command == 'search':
            return 'OK', [b'42' if self.generation == 'old' else b'42 43']
        if command == 'fetch':
            uid = args[0].decode()
            message = EmailMessage()
            message['From'] = 'sender@example.test'
            message['Message-ID'] = f'<{uid}@example.test>'
            message.set_content(uid)
            return 'OK', [(args[0], message.as_bytes())]
        if command == 'store':
            if self.generation == 'old':
                self.state['old_store_started'].set()
                assert self.state['release_old'].wait(10), 'finite old worker not released'
            self.state['stored'].append((self.generation, args[0]))
            return 'OK', []
        raise AssertionError(command)


def test_real_runner_reconnects_before_retired_flag_worker_finishes(monkeypatch, tmp_path):
    monkeypatch.setenv('EMAIL_PASSWORD', 'synthetic-fixture-only')
    monkeypatch.setenv('EMAIL_ALLOWED_USERS', 'sender@example.test')
    monkeypatch.setattr(email_adapter.EmailAdapter, '_seen_uids_snapshot', {})
    monkeypatch.setattr(email_adapter, 'IMAP_FETCH_TIMEOUT_S', 1)
    cfg = PlatformConfig(enabled=True, extra={'address': 'receiver@example.test',
        'imap_host': 'imap.example.test', 'smtp_host': 'smtp.example.test',
        'require_authenticated_sender': False})
    runner = GatewayRunner(GatewayConfig(platforms={Platform.EMAIL: cfg},
                                        sessions_dir=tmp_path / 'sessions'))
    state = {'connections': [], 'calls': [], 'stored': [],
             'old_store_started': threading.Event(), 'release_old': threading.Event()}
    delivered = []
    adapters = []

    async def scenario():
        new_delivered = asyncio.Event()

        def adapter(generation):
            current = email_adapter.EmailAdapter(cfg)
            adapters.append(current)
            monkeypatch.setattr(current, '_connect_imap', lambda: Connection(generation, state))
            monkeypatch.setattr(current, '_probe_smtp', lambda: True)
            current._poll_interval = .05

            async def consume(event):
                delivered.append((generation, event.message_id))
                if generation == 'new':
                    new_delivered.set()

            current.handle_message = consume
            return current

        old = adapter('old')
        runner.adapters[Platform.EMAIL] = old
        runner.delivery_router.adapters = runner.adapters
        runner._running = True
        watcher_requests = []
        # Drive one real reconnect step explicitly; no autonomous provider retry loop.
        monkeypatch.setattr(runner, '_ensure_reconnect_watcher_running',
                            lambda: watcher_requests.append(True))
        old.set_fatal_error_handler(runner._handle_adapter_fatal_error)
        old._running = True
        old._poll_task = asyncio.create_task(old._poll_loop())
        old_poll = old._poll_task
        try:
            assert await asyncio.to_thread(state['old_store_started'].wait, 2)
            async with asyncio.timeout(3):
                while Platform.EMAIL not in runner._failed_platforms or not old_poll.done():
                    await asyncio.sleep(.01)
            assert watcher_requests
            assert Platform.EMAIL not in runner.adapters
            assert not old._running
            assert not state['release_old'].is_set()
            assert not state['stored']
            assert any(not conn.closed for conn in state['connections'])

            fresh = adapter('new')
            monkeypatch.setattr(runner, '_create_adapter', lambda platform, config: fresh)
            await runner._reconnect_failed_platform(Platform.EMAIL, time.monotonic() + 1)
            assert runner.adapters[Platform.EMAIL] is fresh
            assert Platform.EMAIL not in runner._failed_platforms
            await asyncio.wait_for(new_delivered.wait(), 3)
            assert fresh._running
            assert not state['release_old'].is_set()
            assert delivered == [('old', '<42@example.test>'), ('new', '<43@example.test>')]
            assert [args[0] for generation, command, args in state['calls']
                    if generation == 'new' and command == 'fetch'] == [b'43']
            # A late retired-adapter notification cannot evict its healthy successor.
            await runner._handle_adapter_fatal_error(old)
            assert runner.adapters[Platform.EMAIL] is fresh
            assert Platform.EMAIL not in runner._failed_platforms
        finally:
            state['release_old'].set()
            for current in adapters:
                await current.disconnect()
            await asyncio.gather(old_poll, return_exceptions=True)
            pending = tuple(getattr(runner, '_fatal_handler_tasks', ()))
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            await asyncio.get_running_loop().shutdown_default_executor()
            runner.session_store.close_all_db_handles()
        assert all(conn.closed for conn in state['connections'])
        assert ('old', b'42') in state['stored']
        assert delivered == [('old', '<42@example.test>'), ('new', '<43@example.test>')]

    asyncio.run(scenario())
