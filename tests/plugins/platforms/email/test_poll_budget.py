"""The IMAP poll budget covers fetch plus post-handoff flags, not the consumer."""
import asyncio
from email.message import EmailMessage
import threading

from gateway.config import PlatformConfig
from plugins.platforms.email import adapter as email_adapter


class Mailbox:
    capabilities = ()

    def __init__(self, *, block_fetch=False, block_store=False):
        message = EmailMessage()
        message['From'] = 'sender@example.test'
        message['Subject'] = 'Poll budget'
        message['Message-ID'] = '<poll-budget@example.test>'
        message.set_content('Already handed over')
        self.raw = message.as_bytes()
        self.calls = []
        self.fetch_started = threading.Event()
        self.store_started = threading.Event()
        self.fetch_release = threading.Event()
        self.store_release = threading.Event()
        self.flagged = threading.Event()
        self.closed = []
        if not block_fetch:
            self.fetch_release.set()
        if not block_store:
            self.store_release.set()

    def login(self, *_):
        return 'OK', []

    def select(self, *_):
        return 'OK', []

    def logout(self):
        self.closed.append(True)

    def uid(self, command, *args):
        self.calls.append((command, args))
        if command == 'search':
            return 'OK', [b'42']
        if command == 'fetch':
            self.fetch_started.set()
            assert self.fetch_release.wait(10), 'finite fetch fixture was not released'
            return 'OK', [(b'42', self.raw)]
        if command == 'store':
            self.store_started.set()
            assert self.store_release.wait(10), 'finite store fixture was not released'
            self.flagged.set()
            return 'OK', []
        raise AssertionError(command)


def make_adapter(monkeypatch, mailbox):
    monkeypatch.setenv('EMAIL_ALLOWED_USERS', 'sender@example.test')
    monkeypatch.setattr(email_adapter.EmailAdapter, '_seen_uids_snapshot', {})
    adapter = email_adapter.EmailAdapter(PlatformConfig(enabled=True, extra={
        'address': 'receiver@example.test', 'require_authenticated_sender': False}))
    monkeypatch.setattr(adapter, '_connect_imap', lambda: mailbox)
    return adapter


def test_flagging_uses_remaining_poll_budget_and_disconnects(monkeypatch):
    mailbox = Mailbox(block_fetch=True, block_store=True)
    adapter = make_adapter(monkeypatch, mailbox)
    monkeypatch.setattr(email_adapter, 'IMAP_FETCH_TIMEOUT_S', 4)
    delivered = []

    async def consume(event):
        delivered.append(event)

    adapter.handle_message = consume

    async def scenario():
        notified = asyncio.Event()

        async def fatal(current):
            # Exercise the real detached fatal callback -> polling teardown seam.
            await current.disconnect()
            notified.set()

        adapter.set_fatal_error_handler(fatal)
        adapter._running = True
        adapter._poll_interval = .01
        adapter._poll_task = asyncio.create_task(adapter._poll_loop())
        poll = adapter._poll_task
        try:
            assert await asyncio.to_thread(mailbox.fetch_started.wait, 2)
            await asyncio.sleep(2.5)  # consume most of the *shared* 4s I/O budget
            mailbox.fetch_release.set()
            assert await asyncio.to_thread(mailbox.store_started.wait, 2)
            # A new 4s flagging budget cannot pass this; the remaining ~1.5s can.
            await asyncio.wait_for(notified.wait(), timeout=2.5)
            assert not mailbox.flagged.is_set(), 'poll must return before the blocked worker'
            assert not adapter._running
            assert poll.done()
            assert [event.message_id for event in delivered] == ['<poll-budget@example.test>']
            assert adapter._seen_uids == {b'42'}
            assert adapter._seen_uids_snapshot[adapter._address] == {b'42'}
            assert adapter.fatal_error_retryable
            assert 'flag' in adapter.fatal_error_message.lower()
        finally:
            mailbox.fetch_release.set()
            mailbox.store_release.set()
            await adapter.disconnect()
            await asyncio.gather(poll, return_exceptions=True)
            await asyncio.get_running_loop().shutdown_default_executor()
        assert mailbox.flagged.is_set()  # late worker can finish; it was never killed
        assert [command for command, _ in mailbox.calls] == ['search', 'fetch', 'store']
        assert len(mailbox.closed) == 2
        assert len(delivered) == 1  # teardown did not begin an overlapping next poll

    asyncio.run(scenario())


def test_slow_consumer_handoff_does_not_spend_imap_budget(monkeypatch):
    mailbox = Mailbox()
    adapter = make_adapter(monkeypatch, mailbox)
    monkeypatch.setattr(email_adapter, 'IMAP_FETCH_TIMEOUT_S', 1)
    delivered = []

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def consume(event):
            entered.set()
            await release.wait()
            delivered.append(event)

        adapter.handle_message = consume
        poll = asyncio.create_task(adapter._check_inbox())
        try:
            await asyncio.wait_for(entered.wait(), 2)
            await asyncio.sleep(1.2)  # user/agent work outlasts the IMAP-only budget
            assert not poll.done()
            assert not adapter._seen_uids
            release.set()
            await asyncio.wait_for(poll, 2)
        finally:
            release.set()
            await asyncio.gather(poll, return_exceptions=True)
        assert [event.message_id for event in delivered] == ['<poll-budget@example.test>']
        assert mailbox.flagged.is_set()
        assert adapter.fatal_error_code is None
        assert adapter._seen_uids_snapshot[adapter._address] == {b'42'}

    asyncio.run(scenario())
