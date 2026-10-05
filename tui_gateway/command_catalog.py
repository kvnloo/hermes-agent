"""Command catalog accumulation shared by the JSON-RPC catalog builders."""


class CommandCatalog:
    """Accumulator for commands.catalog: ``pairs`` (every [key, desc]), ``canon`` (lowercase
    key/alias → canonical key), ``commands`` (key → desktop meta) and ordered categories."""

    def __init__(self) -> None:
        self.pairs: list[list[str]] = []
        self.canon: dict[str, str] = {}
        self.commands: dict[str, dict[str, str | None]] = {}
        self.cat_map: dict[str, list[list[str]]] = {}  # insertion order = category order

    def add(self, key: str, desc: str, cat: str) -> None:
        self.canon[key.lower()] = key
        self.pairs.append([key, desc])
        self.cat_map.setdefault(cat, []).append([key, desc])
