"""Regression for #156460: a Falcon-blocked pathname must not be checked out.

The contributor must still resolve in release notes, CI attribution and the
mapping writer, without needing the filename that crashes managed Windows.
"""

from scripts import add_contributor, audit_pr_attribution
from scripts.ci.check_contributor_emails import is_mapped as ci_is_mapped
from scripts.releases import authors

EMAIL = "opencode.agent177c@onionmail.org"
LOGIN = "matrixneoaiagent"


def test_falcon_blocked_filename_preserves_contributor_attribution(tmp_path, monkeypatch):
    assert not (authors.CONTRIBUTORS_EMAILS_DIR / EMAIL).exists()
    assert authors.resolve_author("Matrix Neo", EMAIL) == f"@{LOGIN}"
    assert ci_is_mapped(EMAIL, "")
    assert audit_pr_attribution.is_mapped(EMAIL)

    emails_dir = tmp_path / "emails"
    monkeypatch.setattr(add_contributor, "EMAILS_DIR", emails_dir)
    assert add_contributor.add_contributor(EMAIL, LOGIN) == 0
    assert not emails_dir.exists()  # Calling the writer must not recreate the filename.
