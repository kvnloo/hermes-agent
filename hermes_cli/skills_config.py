"""Skills configuration for Hermes Agent. `hermes skills` enters this module."""
from typing import Iterable, List, Optional, Set

from hermes_cli.config import load_config, save_config
from hermes_cli.colors import Colors, color
from hermes_cli.platforms import PLATFORMS as _PLATFORMS

# {key: label} view of the messaging platforms (``PLATFORMS.items()`` / ``.get(key)`` below).
PLATFORMS = {k: info.label for k, info in _PLATFORMS.items() if k != "api_server"}


def get_disabled_skills(config: dict, platform: Optional[str] = None) -> Set[str]:
    """Disabled skill names: the global list unioned with the platform list when given (globally
    disabled stays disabled everywhere) — parsed by the same reader the agent uses."""
    from agent.skill_utils import disabled_skill_names_from
    return disabled_skill_names_from(config.get("skills"), platform)


def allowlist_hidden_skills(config: dict, names: Iterable[str], platform: Optional[str] = None) -> Set[str]:
    """Of *names*, those ``skills.enabled`` / ``platform_enabled`` or an ``external_dirs`` filter hides.
    A ``skills.disabled`` toggle cannot change them, so a UI must neither persist them as disabled
    (that would outlive a later allowlist edit) nor report them as enabled."""
    from agent.skill_utils import skill_visibility_from
    skills_cfg = config.get("skills") if isinstance(config.get("skills"), dict) else {}
    rules = skill_visibility_from({**skills_cfg, "disabled": [], "platform_disabled": {}}, platform)
    return {name for name in names if rules.hides(name)}


def _enabled_patterns(config: dict, platform: Optional[str] = None) -> Optional[Set[str]]:
    """Configured allowlist patterns for this scope; ``None`` means allowlist mode is off.

    Preserve the semantic difference between an absent/null allowlist (default-on) and an explicit
    empty list (allow nothing). Parsing deliberately reuses the runtime matcher.
    """
    from agent.skill_utils import _allowlist
    skills_cfg = config.get("skills") if isinstance(config.get("skills"), dict) else {}
    if platform is None:
        raw = skills_cfg.get("enabled")
    else:
        per_platform = skills_cfg.get("platform_enabled")
        raw = per_platform.get(platform) if isinstance(per_platform, dict) else None
    parsed = _allowlist(raw)
    return None if parsed is None else set(parsed)


def _set_enabled_patterns(config: dict, patterns: Set[str], platform: Optional[str] = None) -> None:
    """Mutate one allowlist scope without saving."""
    config.setdefault("skills", {})
    if platform is None:
        config["skills"]["enabled"] = sorted(patterns)
    else:
        config["skills"].setdefault("platform_enabled", {})
        config["skills"]["platform_enabled"][platform] = sorted(patterns)


def toggle_skill_selection(
    config: dict, name: str, enabled: bool, platform: Optional[str] = None, *, persist: bool = True
) -> str:
    """Persist one UI toggle without forcing users back to ``config.yaml``.

    Returns ``"allowlist"`` when a positive allowlist was changed and ``"denylist"`` when the
    legacy disabled-list path (or a wildcard exception) was used.

    Turning a hidden skill on removes its deny entry first, then adds an exact allowlist entry when
    an active allowlist still excludes it. Turning a skill off removes an exact allowlist entry when
    that alone hides it; if a broader glob/category pattern still admits the skill, an explicit deny
    override is the only lossless representation.

    ``external_dirs`` filters are intentionally not rewritten by a switch: they describe ownership of
    a whole directory, so changing them from a per-skill toggle would be surprising.
    """
    from copy import deepcopy
    from agent.skill_utils import ESSENTIAL_SKILLS, skill_visibility_from
    from hermes_cli import managed_scope

    name = str(name or "").strip()
    if not name:
        raise ValueError("skill name is required")
    if not enabled and name in ESSENTIAL_SKILLS:
        raise ValueError(f"Skill '{name}' is essential to Hermes and cannot be disabled.")

    working = deepcopy(config)
    skills_cfg = working.setdefault("skills", {})
    if not isinstance(skills_cfg, dict):
        skills_cfg = {}
        working["skills"] = skills_cfg

    # A platform toggle may narrow a global policy, but cannot override a global explicit deny.
    global_disabled = get_disabled_skills(working)
    if enabled and platform is not None and name in global_disabled:
        raise ValueError(
            f"Skill '{name}' is disabled globally; enable it in the global skills view first."
        )

    if platform is None:
        disabled = get_disabled_skills(working)
    else:
        from agent.skill_utils import _normalize_string_set
        per = skills_cfg.get("platform_disabled")
        raw = per.get(platform) if isinstance(per, dict) else None
        disabled = _normalize_string_set(raw)

    if enabled:
        disabled.discard(name)
        if platform is None:
            skills_cfg["disabled"] = sorted(disabled)
        else:
            skills_cfg.setdefault("platform_disabled", {})[platform] = sorted(disabled)

        reason = skill_visibility_from(skills_cfg, platform).hidden_reason(name)
        if reason == "filtered":
            raise ValueError(
                f"Skill '{name}' is excluded by skills.external_dirs; edit that directory filter to enable it."
            )
        if reason == "not_enabled":
            patterns = _enabled_patterns(working, platform)
            allow_key = "skills.enabled" if platform is None else f"skills.platform_enabled.{platform}"
            if patterns is None or managed_scope.is_key_managed(allow_key):
                if platform is not None and _enabled_patterns(working) is not None:
                    raise ValueError(
                        f"Skill '{name}' is outside the global skills.enabled allowlist; "
                        "enable it in the global skills view first."
                    )
                raise ValueError(f"Skill '{name}' is outside an allowlist that this view cannot edit.")
            patterns.add(name)
            _set_enabled_patterns(working, patterns, platform)
            remaining = skill_visibility_from(working.get("skills"), platform).hidden_reason(name)
            if remaining == "not_enabled" and platform is not None:
                raise ValueError(
                    f"Skill '{name}' is outside the global skills.enabled allowlist; "
                    "enable it in the global skills view first."
                )
            if remaining == "filtered":
                raise ValueError(
                    f"Skill '{name}' is excluded by skills.external_dirs; edit that directory filter to enable it."
                )
            mode = "allowlist"
        else:
            mode = "denylist"
    else:
        mode = "denylist"
        patterns = _enabled_patterns(working, platform)
        allow_key = "skills.enabled" if platform is None else f"skills.platform_enabled.{platform}"
        if patterns is not None and name in patterns and not managed_scope.is_key_managed(allow_key):
            patterns.remove(name)
            _set_enabled_patterns(working, patterns, platform)
            if skill_visibility_from(working.get("skills"), platform).hides(name):
                mode = "allowlist"
            else:
                disabled.add(name)
        else:
            disabled.add(name)

        if platform is None:
            skills_cfg["disabled"] = sorted(disabled)
        else:
            skills_cfg.setdefault("platform_disabled", {})[platform] = sorted(disabled)

    # Keep the caller's object identity because several config UIs retain it across section writes.
    config.clear()
    config.update(working)
    if persist:
        save_config(config)
    return mode


def managed_locked_skills(names: Iterable[str], platform: Optional[str] = None) -> Set[str]:
    """Skills a config UI must show as locked.

    This includes Hermes' essential skills plus names the administrator's managed scope decides:
    skills hidden by its pinned rules, or every skill when the list a toggle would write is pinned.
    """
    from agent.skill_utils import ESSENTIAL_SKILLS, skill_visibility_from
    from hermes_cli import managed_scope
    names = set(names)
    locked = names & ESSENTIAL_SKILLS
    target = "skills.disabled" if platform is None else f"skills.platform_disabled.{platform}"
    if managed_scope.is_key_managed(target):
        return names
    pinned = skill_visibility_from(managed_scope.load_managed_config().get("skills"), platform)
    return locked | {
        name for name in names if pinned.hidden_reason(name) in ("disabled", "not_enabled")
    }


def save_disabled_skills(config: dict, disabled: Set[str], platform: Optional[str] = None):
    """Persist disabled skill names to config; essential skills (e.g. ``hermes-agent``) are
    silently dropped — they cannot be disabled from any surface."""
    from agent.skill_utils import ESSENTIAL_SKILLS
    disabled = set(disabled) - ESSENTIAL_SKILLS
    config.setdefault("skills", {})
    if platform is None:
        config["skills"]["disabled"] = sorted(disabled)
    else:
        config["skills"].setdefault("platform_disabled", {})
        config["skills"]["platform_disabled"][platform] = sorted(disabled)
    save_config(config)


def _list_all_skills() -> List[dict]:
    """Return all installed skills (ignoring disabled state)."""
    try:
        from tools.skills_tool import _find_all_skills
        return _find_all_skills(skip_disabled=True)
    except Exception:
        return []


def _get_categories(skills: List[dict]) -> List[str]:
    """Return sorted unique category names (None -> 'uncategorized')."""
    return sorted({s["category"] or "uncategorized" for s in skills})


def _select_platform() -> Optional[str]:
    """Ask which platform to configure; None means global."""
    options = [("global", "All platforms (global default)")] + list(PLATFORMS.items())
    print()
    print(color("  Configure skills for:", Colors.BOLD))
    for i, (key, label) in enumerate(options, 1):
        print(f"  {i}. {label}")
    print()
    try:
        raw = input(color("  Select [1]: ", Colors.YELLOW)).strip()
    except (KeyboardInterrupt, EOFError):
        return None
    try:
        idx = int(raw) - 1  # empty input -> ValueError -> global
    except ValueError:
        return None
    if 0 <= idx < len(options) and options[idx][0] != "global":
        return options[idx][0]
    return None


def _toggle_by_category(skills: List[dict], visible: Set[str]) -> Set[str]:
    """Toggle all skills in a category at once; returns the names left on."""
    from hermes_cli.curses_ui import curses_checklist
    categories = _get_categories(skills)
    cat_skills = [{s["name"] for s in skills if (s["category"] or "uncategorized") == cat}
                  for cat in categories]
    cat_labels = [f"{cat} ({len(names)} skills)" for cat, names in zip(categories, cat_skills)]
    # A category is "enabled" (checked) while any of its skills is visible
    pre_selected = {i for i, names in enumerate(cat_skills) if names & visible}
    chosen = curses_checklist("Categories — toggle entire categories",
                              cat_labels, pre_selected, cancel_returns=pre_selected)
    return set().union(*(names for i, names in enumerate(cat_skills) if i in chosen))


def skills_command(args=None):
    """Entry point for `hermes skills`."""
    from hermes_cli.curses_ui import curses_checklist
    config = load_config()
    skills = _list_all_skills()
    if not skills:
        print(color("  No skills installed.", Colors.DIM))
        return

    platform = _select_platform()
    platform_label = PLATFORMS.get(platform, "All platforms") if platform else "All platforms"
    print()
    print(color(f"  Configure for: {platform_label}", Colors.DIM))
    print()
    print("  1. Toggle individual skills")
    print("  2. Toggle by category")
    print()
    try:
        mode = input(color("  Select [1]: ", Colors.YELLOW)).strip() or "1"
    except (KeyboardInterrupt, EOFError):
        return

    from agent.skill_utils import skill_visibility_from
    visibility = skill_visibility_from(config.get("skills"), platform)
    visible = {s["name"] for s in skills if not visibility.hides(s["name"])}
    locked = managed_locked_skills((s["name"] for s in skills), platform)
    if mode == "2":
        chosen_on = _toggle_by_category(skills, visible)
    else:
        labels = [f"{s['name']}  ({s['category'] or 'uncategorized'})  —  {s['description'][:55]}"
                  + ("  [locked by administrator]" if s["name"] in locked else "") for s in skills]
        # "selected" = visible — matches the [✓] convention
        pre_selected = {i for i, s in enumerate(skills) if s["name"] in visible}
        chosen = curses_checklist(f"Skills for {platform_label}",
                                  labels, pre_selected, cancel_returns=pre_selected)
        chosen_on = {skills[i]["name"] for i in chosen}
    # Managed-scope skills keep their state: the administrator's pin wins over any write.
    if touched := sorted((chosen_on ^ visible) & locked):
        print(color(f"  Locked by your administrator (managed scope), left unchanged: {', '.join(touched)}",
                    Colors.YELLOW))

    changed = sorted((chosen_on ^ visible) - locked)
    if not changed:
        print(color("  No changes.", Colors.DIM))
        return

    blocked = []
    before = config.copy()
    for name in changed:
        try:
            toggle_skill_selection(config, name, name in chosen_on, platform, persist=False)
        except ValueError as exc:
            blocked.append(str(exc))

    if config == before:
        for message in blocked:
            print(color(f"  {message}", Colors.YELLOW))
        print(color("  No changes.", Colors.DIM))
        return

    save_config(config)
    for message in blocked:
        print(color(f"  {message}", Colors.YELLOW))

    final_visibility = skill_visibility_from(config.get("skills"), platform)
    enabled_count = sum(1 for s in skills if not final_visibility.hides(s["name"]))
    print(color(f"✓ Saved: {enabled_count} enabled, {len(skills) - enabled_count} disabled ({platform_label}).",
                Colors.GREEN))
