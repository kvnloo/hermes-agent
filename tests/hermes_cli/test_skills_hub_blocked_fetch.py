"""Regression coverage for URL-safety-blocked Skills Hub downloads (#149201)."""

from contextlib import nullcontext
from io import StringIO
from types import SimpleNamespace

from rich.console import Console


def test_blocked_bundle_is_not_reported_as_stale_and_reason_does_not_leak(monkeypatch):
    import hermes_cli.skills_hub as cli_hub
    import tools.skills_hub as hub
    from tools.skills_hub_models import SkillMeta

    class Source:
        blocked = True

        def source_id(self):
            return "clawhub"

        def inspect(self, _identifier):
            return SkillMeta("example", "", "clawhub", "clawhub/example", "community")

        def fetch(self, _identifier):
            hub._guarded_http_get("https://clawhub.ai/api/v1/download")
            return None

    source = Source()
    not_found = SimpleNamespace(status_code=404, headers={})
    client = SimpleNamespace(get=lambda *_args, **_kwargs: not_found)
    monkeypatch.setattr(cli_hub, "_sources", lambda: [source])
    monkeypatch.setattr(hub, "create_ssrf_safe_client", lambda **_kwargs: nullcontext(client))
    monkeypatch.setattr(hub, "is_safe_url", lambda _url: not source.blocked)
    monkeypatch.setattr(hub, "check_website_access", lambda _url: None)

    sink = StringIO()
    console = Console(file=sink, force_terminal=False, color_system=None, width=200)

    assert cli_hub.do_install(
        "clawhub/example", console=console, skip_confirm=True
    ) is False
    blocked_output = sink.getvalue()
    assert "blocked by the URL-safety guard" in blocked_output
    assert "security.fake_ip_ranges" in blocked_output
    assert "Stale index entry" not in blocked_output

    sink.seek(0)
    sink.truncate()
    source.blocked = False

    assert cli_hub.do_install(
        "clawhub/example", console=console, skip_confirm=True
    ) is False
    stale_output = sink.getvalue()
    assert "Stale index entry" in stale_output
    assert "URL-safety guard" not in stale_output

def test_pooled_github_fetch_rejects_fake_ip_dns_without_stale_index(monkeypatch):
    """A GitHub-backed indexed skill must report a blocked download, not a stale entry."""
    import socket

    import hermes_cli.skills_hub as cli_hub
    import tools.skills_hub as hub
    import tools.url_safety as safety
    from tools.skills_hub_github import GitHubSource
    from tools.skills_hub_models import SkillMeta

    def fake_dns(_host, _port=0):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP,
                 "", ("198.18.0.23", 443))]

    def get(url, **_kwargs):
        assert url.startswith("https://api.github.com/")
        safety._resolved_http_connect_ips("api.github.com", 443, "https")
        raise AssertionError("the fake-IP address must be rejected before connecting")

    monkeypatch.setattr(safety, "_getaddrinfo", fake_dns)
    monkeypatch.setattr(safety, "_global_allow_private_urls", lambda: False)
    monkeypatch.setattr(safety, "_allows_private_ip_resolution", lambda _host, _scheme: False)
    monkeypatch.setattr(hub, "create_ssrf_safe_client",
                        lambda **_kwargs: nullcontext(SimpleNamespace(get=get)))

    class Source:
        def source_id(self):
            return "hermes-index"

        def inspect(self, _identifier):
            return SkillMeta("example", "", "hermes-index",
                             "hermes-index/example", "community")

        def fetch(self, _identifier):
            github = GitHubSource(auth=SimpleNamespace(get_headers=lambda: {}))
            return github._github_json("https://api.github.com/repos/example/skills")

    monkeypatch.setattr(cli_hub, "_sources", lambda: [Source()])
    output = StringIO()
    console = Console(file=output, force_terminal=False, color_system=None, width=200)
    assert cli_hub.do_install("hermes-index/example", console=console, skip_confirm=True) is False
    assert "blocked by the URL-safety guard" in output.getvalue()
    assert "Stale index entry" not in output.getvalue()
