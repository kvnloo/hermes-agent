"""An owned WhatsApp bridge must stay in the gateway's Windows job.

Regression for #68128 and the bridge owner-death contract of #127047.
"""

from unittest.mock import patch

import pytest

from hermes_cli._subprocess_compat import (
    windows_detach_flags,
    windows_detach_flags_without_breakaway,
)
from plugins.platforms.whatsapp import adapter


@pytest.mark.platforms("windows")
def test_bridge_spawn_stays_in_gateway_job_even_when_breakaway_is_allowed():
    argv = ["node", "bridge.js"]
    log = object()
    env = {"HERMES_HOME": "test-home"}
    process = object()

    with patch.object(adapter, "spawn_owned", return_value=process) as spawn:
        assert adapter._spawn_bridge_process(argv, log, env) is process

    expected = windows_detach_flags_without_breakaway()
    assert windows_detach_flags() & 0x01000000  # CREATE_BREAKAWAY_FROM_JOB
    assert expected & 0x01000000 == 0
    spawn.assert_called_once_with(
        argv,
        purpose="whatsapp-bridge",
        stdin=adapter.subprocess.DEVNULL,
        stdout=log,
        stderr=log,
        env=env,
        creationflags=expected,
    )
