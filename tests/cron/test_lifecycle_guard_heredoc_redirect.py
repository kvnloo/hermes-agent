"""Quoted cat heredoc data remains inert across output-path expansion (#152447)."""

import pytest

from cron.lifecycle_guard import scan_gateway_lifecycle
from tools.shell_heredoc import strip_inert_heredoc_bodies


@pytest.mark.parametrize(
    "opener",
    [
        pytest.param(
            '''cat > "$(cygpath -m "$TMPDIR")/x.py" <<'EOF'\n''',
            id="substitution-in-redirect-target",
        ),
        pytest.param(
            '''V=$(uname -s); cat > ./x.py <<'EOF'\n''',
            id="unrelated-substitution-before-cat",
        ),
        pytest.param(
            """cat > ./x.py <<'EOF'\n""",
            id="literal-redirect-control",
        ),
    ],
)
def test_cat_quoted_redirect_body_is_not_executed(tmp_path, opener):
    data = tmp_path / "data" / "raw" / "train.parquet"
    data.parent.mkdir(parents=True)
    data.write_bytes(b"PAR1" + b"\x00" * (2 * 1024 * 1024))
    body = 'import pandas as pd\ntrain = pd.read_parquet("data/raw/train.parquet")\n'
    command = opener + body + "EOF\n"

    assert "train.parquet" not in strip_inert_heredoc_bodies(command)
    assert scan_gateway_lifecycle(command, cwd=str(tmp_path)) == (False, None)


@pytest.mark.parametrize(
    "command",
    [
        "bash <<'EOF'\nhermes gateway stop\nEOF\n",
        "$(echo bash) <<'EOF'\nhermes gateway stop\nEOF\n",
        "cat > >(bash) <<'EOF'\nhermes gateway stop\nEOF\n",
        "cat <<EOF\n$(hermes gateway stop)\nEOF\n",
    ],
)
def test_executable_heredoc_stays_visible(tmp_path, command):
    assert "hermes gateway stop" in strip_inert_heredoc_bodies(command)
    assert scan_gateway_lifecycle(command, cwd=str(tmp_path)) == (True, None)
