"""Catalog disclosure regression for NousResearch/hermes-agent#153377."""

from hermes_cli.plugin_catalog import get_catalog_entry


def test_mediarag_disclosure_is_one_bullet_block():
    entry = get_catalog_entry("mediarag")
    assert entry is not None
    lead, separator, disclosures = entry.description.partition("\n\nDisclosures\n\n")
    assert lead and separator and disclosures
    assert all(line.startswith("- ") for line in disclosures.splitlines())
    assert "Disclosure —" not in disclosures
    # Both optional remote adapters access tokens, so both must be visible to users.
    assert "RAINDROP_API_TOKEN" in disclosures
    assert "NOTION_TOKEN" in disclosures
