"""Catalog admission regression: the follow-through install must resolve to its published source.

The catalog parser accepts any HTTPS URL, so an unexpanded template owner
can look valid but make both install and the documentation screenshot fail.
"""

from urllib.parse import urlsplit

from hermes_cli.plugin_catalog import get_catalog_entry


def test_follow_through_install_origin_matches_admission_metadata():
    entry = get_catalog_entry("follow-through")
    assert entry is not None, "follow-through must be installable by catalog name"

    origin = urlsplit(entry.install_identifier)
    assert (origin.scheme, origin.netloc) == ("https", "github.com")
    parts = origin.path.strip("/").removesuffix(".git").split("/")
    assert len(parts) == 2 and parts[1] == "follow-through"

    owner, repo = parts
    assert owner.casefold() not in {"replace_owner", "owner"}
    assert entry.maintainer.casefold() == owner.casefold()

    # Artwork must describe the same reviewed source and pin as the install.
    for screenshot in entry.screenshots:
        image = urlsplit(screenshot)
        assert (image.scheme, image.netloc) == ("https", "raw.githubusercontent.com")
        assert image.path.startswith(f"/{owner}/{repo}/{entry.sha}/")
