"""F12: offline census of a catalog plugin at its pinned SHA.

Static only: the plugin's code is parsed (ast), never imported or executed. Optionally (with
--hermes-tree) the static sub-checks of ``hermes plugins validate`` are called as library functions
from that hermes tree, EXCLUDING the capability probe (the one check that imports and runs the
plugin). The capability verdict is then predicted from the AST census and labelled MODELED.

Checks per plugin:
  1. pin: clone HEAD == pinned sha, the sha is a commit reachable from the default branch
  2. registrations reachable from register() (tools / hooks / middleware / commands), via ast
  3. plugin manifest provides_* vs registrations (the validate capability rule, rule 6)
  4. catalog entry capabilities vs registrations (rule 6, catalog side)
  5. internal-path imports (anything from the hermes tree's top-level packages; ctx-only rule)
  6. sys.path mutations
  7. imports that do not resolve under the catalog install layout (subdir-only sparse checkout)
  8. self-updater signals (the CI regex for JS bundles, plus Python fetch-and-replace signals)
  9. desktop surface (desktop/plugin.js present?)
 10. dependency declarations and upper bounds (rule 9)
 11. hermes static validate sub-checks (manifest fields, requires_env, loadable, deps, security scan,
     desktop surface, language packs, built-in tool collisions)

Usage:
  python f12_census.py --clone DIR --repo URL --sha SHA --subdir PATH --catalog-entry YAML
                       [--hermes-tree DIR] [--variant NAME] [--context-methods-out JSON] > out.json
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REG_METHODS = {
    "register_tool": ("tools", ("name",)),
    "register_hook": ("hooks", ("hook_name",)),
    "register_middleware": ("middleware", ("kind",)),
    "register_command": ("commands", ("name",)),
    "register_cli_command": ("commands", ("name",)),
}
EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache"}
JS_EXT = {".js", ".mjs", ".cjs", ".ts"}
SELF_UPDATE_FETCH = re.compile(r"releases/latest|raw\.githubusercontent\.com")
SELF_UPDATE_WRITE = re.compile(r"writeTextFile|renamePath|writeFile\(")
PY_SELF_UPDATE = re.compile(r"git\s+(pull|fetch|reset)|pip\s+install|releases/latest|self[_-]?update", re.I)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(clone: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True,
                          check=False).stdout.strip()


def load_yaml(path: Path):
    try:
        import yaml  # PyYAML
        return yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except ImportError:  # pragma: no cover
        import hermes_yaml
        return hermes_yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def py_files(root: Path):
    for f in sorted(root.rglob("*.py")):
        if not any(part in EXCLUDED_DIRS for part in f.relative_to(root).parts):
            yield f


def module_constants(tree: ast.Module) -> dict:
    """Module-level NAME = <literal> bindings (str or dict literal), for resolving call args."""
    out: dict = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:
                pass
    return out


def resolve(node: ast.AST | None, consts: dict):
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and isinstance(consts.get(node.id), str):
        return consts[node.id]
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
            and isinstance(consts.get(node.value.id), dict)):
        key = resolve(node.slice, consts)
        val = consts[node.value.id].get(key) if key is not None else None
        if isinstance(val, str):
            return val
    return "<dynamic:" + ast.unparse(node) + ">"


class FunctionScan(ast.NodeVisitor):
    """Registrations and local calls inside one function body (aliases via getattr / attribute)."""

    def __init__(self, consts: dict):
        self.consts = consts
        self.aliases: dict[str, str] = {}
        self.regs: list[dict] = []
        self.calls: set[str] = set()

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = node.value
            method = None
            if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "getattr"
                    and len(v.args) >= 2 and isinstance(v.args[1], ast.Constant)):
                method = v.args[1].value
            elif isinstance(v, ast.Attribute):
                method = v.attr
            if method in REG_METHODS:
                self.aliases[node.targets[0].id] = method
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        method = None
        if isinstance(node.func, ast.Attribute) and node.func.attr in REG_METHODS:
            method = node.func.attr
        elif isinstance(node.func, ast.Name):
            if node.func.id in self.aliases:
                method = self.aliases[node.func.id]
            else:
                self.calls.add(node.func.id)
        if method:
            kind, kw_names = REG_METHODS[method]
            arg = next((k.value for k in node.keywords if k.arg in kw_names), None)
            if arg is None and node.args:
                arg = node.args[0]
            self.regs.append({"method": method, "kind": kind, "key": resolve(arg, self.consts),
                              "line": node.lineno})
        self.generic_visit(node)


def scan_module(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    consts = module_constants(tree)
    funcs: dict[str, FunctionScan] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fs = FunctionScan(consts)
            fs.visit(node)
            funcs[node.name] = fs
    return {"tree": tree, "funcs": funcs}


def reachable_regs(mod: dict, entry: str) -> list[dict]:
    seen, stack, regs = set(), [entry], []
    while stack:
        name = stack.pop()
        if name in seen or name not in mod["funcs"]:
            continue
        seen.add(name)
        fs = mod["funcs"][name]
        regs.extend(dict(r, via=name) for r in fs.regs)
        stack.extend(fs.calls)
    return regs


def imports_of(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name.split(".")[0], node.lineno, 0
        elif isinstance(node, ast.ImportFrom):
            yield (node.module or "").split(".")[0], node.lineno, node.level


def syspath_mutations(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"insert", "append", "extend"}
                and ast.unparse(node.func.value) == "sys.path"):
            yield {"line": node.lineno, "expr": ast.unparse(node)}


EXEC_CALLS = {"subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call",
              "subprocess.check_output", "os.system", "os.popen", "os.execv", "os.execvp", "os.execl"}
WRITE_CALLS = {"open", "write_text", "write_bytes", "shutil.copy", "shutil.copyfile", "shutil.move",
               "os.replace", "os.rename"}
FETCH_CALLS = {"urllib.request.urlopen", "urlopen", "httpx.get", "httpx.stream", "requests.get"}


def py_self_update_calls(path: Path, rel: str) -> list[dict]:
    """Executable fetch-and-replace signals: an exec call whose string args run git/pip, a write whose
    args mention __file__, or a network fetch call in the plugin's own code."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
        tail = name.rsplit(".", 1)[-1]
        strings = " ".join(n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str))
        if name in EXEC_CALLS and PY_SELF_UPDATE.search(strings):
            hits.append({"file": rel, "line": node.lineno, "kind": "exec-git-or-pip", "call": name})
        elif (name in WRITE_CALLS or tail in {"write_text", "write_bytes"}) and "__file__" in ast.unparse(node):
            hits.append({"file": rel, "line": node.lineno, "kind": "writes-own-file", "call": name})
        elif name in FETCH_CALLS:
            hits.append({"file": rel, "line": node.lineno, "kind": "network-fetch", "call": name})
    return hits


def hermes_top_level(hermes_tree: Path | None) -> set[str]:
    if hermes_tree is None:
        return {"hermes_cli", "agent", "tools", "gateway", "tui_gateway", "cron", "providers",
                "hermes_state", "hermes_constants", "run_agent", "model_tools", "toolsets", "pm"}
    names = set()
    for p in hermes_tree.iterdir():
        if p.is_dir() and (p / "__init__.py").is_file() and p.name not in {"tests", "plugins", "scripts"}:
            names.add(p.name)
        elif p.suffix == ".py" and p.stem not in {"setup", "conftest"}:
            names.add(p.stem)
    return names


def dist_to_module(req: str) -> str:
    name = re.split(r"[\s<>=!~;\[@(]", req.strip(), maxsplit=1)[0]
    return name.lower().replace("-", "_").replace(".", "_")


def has_upper_bound(req: str) -> bool:
    spec = req.split(";", 1)[0]
    return bool(re.search(r"<|~=|==|===", spec))


def read_pyproject_deps(path: Path) -> list[str] | None:
    if not path.is_file():
        return None
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return list(((data.get("project") or {}).get("dependencies")) or [])


def diff_caps(declared: dict, actual: dict) -> dict:
    out = {}
    for kind, key in (("tools", "provides_tools"), ("hooks", "provides_hooks"),
                      ("middleware", "provides_middleware")):
        d = set(declared.get(key) or [])
        a = set(actual.get(kind) or [])
        out[kind] = {"declared": sorted(d), "registered": sorted(a),
                     "undeclared": sorted(a - d), "unregistered": sorted(d - a),
                     "match": a == d}
    return out


def hermes_static_checks(hermes_tree: Path, plugin_dir: Path, manifest: dict, recorded: dict) -> dict:
    sys.path.insert(0, str(hermes_tree))
    import hermes_cli.plugin_validate as pv
    from hermes_cli.plugin_validate_desktop import check_desktop_surface
    from hermes_cli.plugin_validate_locales import check_language_packs

    origin = Path(pv.__file__).resolve()
    assert hermes_tree.resolve() in origin.parents, f"hermes_cli imported from {origin}, not {hermes_tree}"
    report = pv.ValidationReport()
    steps = [
        ("manifest fields", lambda: pv._check_manifest_fields(report, manifest)),
        ("requires_hermes", lambda: pv._check_requires_hermes(report, manifest)),
        ("config schema", lambda: pv._check_config_spec(report, manifest)),
        ("requires_env", lambda: pv._check_requires_env(report, manifest)),
        ("loadable", lambda: pv._check_loadable(report, plugin_dir, manifest)),
        ("python dependencies", lambda: pv._check_python_dependencies(report, plugin_dir)),
        ("built-in tool collisions", lambda: pv._check_builtin_collisions(report, manifest, recorded)),
        ("security scan", lambda: pv._check_security_scan(report, plugin_dir)),
        ("desktop surface", lambda: check_desktop_surface(report, plugin_dir)),
        ("language packs", lambda: check_language_packs(report, manifest, plugin_dir)),
    ]
    errors = {}
    for name, fn in steps:
        try:
            fn()
        except Exception as exc:  # recorded, never hidden
            errors[name] = f"{type(exc).__name__}: {exc}"
    builtin = pv._builtin_tool_names()  # returns [] on any discovery error, so record the size
    from tools.plugin_guard import scan_plugin, PLUGIN_SCANNER_VERSION
    scan = scan_plugin(plugin_dir)
    from hermes_cli.plugins import PluginContext
    ctx_methods = sorted(n for n in dir(PluginContext)
                         if not n.startswith("_") and callable(getattr(PluginContext, n)))
    return {
        "hermes_cli_origin": str(origin.parent),
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in report.checks],
        "warnings": list(report.warnings),
        "errors": errors,
        "excluded": ["capability probe (imports and runs the plugin; see E52 / T1 probe)"],
        "builtin_tool_registry": {"size": len(builtin),
                                  "collisions": sorted(set(recorded.get("tools") or []) & set(builtin))},
        "security_scan": {"scanner": PLUGIN_SCANNER_VERSION, "verdict": scan.verdict,
                          "findings": [{"pattern": f.pattern_id, "severity": f.severity,
                                        "file": f.file, "line": f.line} for f in scan.findings]},
        "_context_methods": ctx_methods,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", type=Path, required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--subdir", default="")
    ap.add_argument("--catalog-entry", type=Path, required=True)
    ap.add_argument("--hermes-tree", type=Path)
    ap.add_argument("--variant", default="as-pinned")
    ap.add_argument("--plugin-dir-override", type=Path,
                    help="census this directory instead of <clone>/<subdir> (synthetic variants)")
    ap.add_argument("--context-methods-out", type=Path)
    a = ap.parse_args()

    clone = a.clone.resolve()
    plugin_dir = (a.plugin_dir_override or (clone / a.subdir if a.subdir else clone)).resolve()
    head = git(clone, "rev-parse", "HEAD")
    pin = {
        "repo": a.repo, "sha": a.sha, "subdir": a.subdir,
        "clone_head": head, "head_matches_pin": head == a.sha,
        "object_type": git(clone, "cat-file", "-t", a.sha),
        "reachable_from_default_branch": subprocess.run(
            ["git", "-C", str(clone), "merge-base", "--is-ancestor", a.sha, "origin/HEAD"],
            check=False).returncode == 0,
        "default_branch_head": git(clone, "rev-parse", "origin/HEAD"),
    }

    manifest_path = next((plugin_dir / n for n in ("plugin.yaml", "plugin.yml") if (plugin_dir / n).is_file()), None)
    manifest = load_yaml(manifest_path) if manifest_path else {}
    catalog = load_yaml(a.catalog_entry)

    init = plugin_dir / "__init__.py"
    regs = reachable_regs(scan_module(init), "register") if init.is_file() else []
    actual = {k: sorted({r["key"] for r in regs if r["kind"] == k})
              for k in ("tools", "hooks", "middleware", "commands")}
    deferred = []
    if (plugin_dir / "tools.py").is_file():
        deferred = reachable_regs(scan_module(plugin_dir / "tools.py"), "register_tools")

    internal = hermes_top_level(a.hermes_tree)
    stdlib = set(sys.stdlib_module_names)
    files = list(py_files(plugin_dir))
    local_mods = {p.stem for p in plugin_dir.glob("*.py")} | {p.name for p in plugin_dir.iterdir() if p.is_dir()}
    plugin_pyproject = read_pyproject_deps(plugin_dir / "pyproject.toml")
    manifest_deps = list(manifest.get("python_dependencies") or [])
    declared_deps = (plugin_pyproject or []) + manifest_deps
    declared_mods = {dist_to_module(r) for r in declared_deps}
    repo_root = clone

    internal_imports, unresolved, syspath = [], [], []
    for f in files:
        rel = str(f.relative_to(plugin_dir))
        syspath.extend(dict(m, file=rel) for m in syspath_mutations(f))
        for mod, line, level in imports_of(f):
            if level or not mod or mod == "__future__":
                continue
            if mod in internal:
                internal_imports.append({"file": rel, "line": line, "module": mod})
            elif mod in stdlib or mod in local_mods or mod in declared_mods:
                continue
            else:
                in_full_clone = (repo_root / "src" / mod).is_dir() or (repo_root / mod).is_dir()
                unresolved.append({"file": rel, "line": line, "module": mod,
                                   "resolvable_in_full_clone_via_syspath": in_full_clone,
                                   "resolvable_in_catalog_install_layout": False})

    transitive = {}
    for u in unresolved:
        pkg = repo_root / "src" / u["module"]
        if pkg.is_dir() and u["module"] not in transitive:
            third = set()
            for f in py_files(pkg):
                for mod, _l, level in imports_of(f):
                    if not level and mod and mod not in stdlib and mod != u["module"] and mod != "__future__":
                        third.add(mod)
            transitive[u["module"]] = sorted(third)

    self_update = {"js_ci_rule_hits": [], "py_signals": []}
    for f in sorted(plugin_dir.rglob("*")):
        if not f.is_file() or any(p in EXCLUDED_DIRS for p in f.relative_to(plugin_dir).parts):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        rel = str(f.relative_to(plugin_dir))
        if f.suffix in JS_EXT and SELF_UPDATE_FETCH.search(text) and SELF_UPDATE_WRITE.search(text):
            self_update["js_ci_rule_hits"].append(rel)
        if f.suffix == ".py":
            self_update["py_signals"].extend(py_self_update_calls(f, rel))
            for i, line in enumerate(text.splitlines(), 1):
                if PY_SELF_UPDATE.search(line):
                    self_update.setdefault("doc_or_string_mentions", []).append(
                        {"file": rel, "line": i, "text": line.strip()[:160]})

    root_deps = read_pyproject_deps(repo_root / "pyproject.toml") or []
    deps = {
        "plugin_dir_pyproject": plugin_pyproject,
        "manifest_python_dependencies": manifest_deps,
        "declared_for_install": declared_deps,
        "declared_without_upper_bound": [r for r in declared_deps if not has_upper_bound(r)],
        "repo_root_pyproject": root_deps,
        "repo_root_without_upper_bound": [r for r in root_deps if not has_upper_bound(r)],
    }

    recorded = {"tools": actual["tools"], "hooks": actual["hooks"], "middleware": actual["middleware"],
                "commands": actual["commands"], "providers": []}
    manifest_vs_code = diff_caps(manifest, actual)
    catalog_vs_code = diff_caps(catalog.get("capabilities") or {}, actual)
    predicted_capability_fail = [f"undeclared {k} registered: {', '.join(v['undeclared'])}"
                                 for k, v in manifest_vs_code.items() if v["undeclared"]]

    out = {
        "schema": "f12.census.v1",
        "variant": a.variant,
        "census_script_sha256": sha256_file(Path(__file__)),
        "plugin_dir": str(plugin_dir.relative_to(clone)) if plugin_dir.is_relative_to(clone) else str(plugin_dir),
        "pin": pin,
        "manifest": {"path": manifest_path.name if manifest_path else None,
                     "sha256": sha256_file(manifest_path) if manifest_path else None,
                     "name": manifest.get("name"), "kind": manifest.get("kind"),
                     "provides_tools": manifest.get("provides_tools"),
                     "provides_hooks": manifest.get("provides_hooks"),
                     "provides_middleware": manifest.get("provides_middleware"),
                     "requires_env": manifest.get("requires_env")},
        "catalog_entry": {"path": str(a.catalog_entry.name), "sha256": sha256_file(a.catalog_entry),
                          "name": catalog.get("name"), "sha": catalog.get("sha"),
                          "subdir": catalog.get("subdir"),
                          "name_matches_manifest": catalog.get("name") == manifest.get("name"),
                          "sha_matches_pin": catalog.get("sha") == a.sha,
                          "subdir_matches": (catalog.get("subdir") or "") == a.subdir},
        "registrations": {"from_register": regs, "summary": actual,
                          "deferred_tools_py_register_tools": deferred,
                          "label": "OBSERVED (ast of plugin source; not executed)"},
        "manifest_vs_registrations": manifest_vs_code,
        "catalog_vs_registrations": catalog_vs_code,
        "predicted_validate_capability_check": {
            "result": "FAIL" if predicted_capability_fail else "PASS",
            "reasons": predicted_capability_fail,
            "label": "MODELED (hermes plugin_validate._check_capabilities rule applied to the ast census)"},
        "internal_path_imports": internal_imports,
        "syspath_mutations": syspath,
        "unresolved_under_catalog_install_layout": unresolved,
        "out_of_subdir_package_third_party_imports": transitive,
        "self_updater": self_update,
        "desktop_bundle_present": (plugin_dir / "desktop" / "plugin.js").is_file(),
        "dependencies": deps,
        "counts": {
            "capability_mismatch_manifest": sum(len(v["undeclared"]) + len(v["unregistered"]) for v in manifest_vs_code.values()),
            "capability_mismatch_catalog": sum(len(v["undeclared"]) + len(v["unregistered"]) for v in catalog_vs_code.values()),
            "internal_path_imports": len(internal_imports),
            "syspath_mutations": len(syspath),
            "unresolved_imports_catalog_layout": len(unresolved),
            "self_updater_signals": len(self_update["js_ci_rule_hits"]) + len(self_update["py_signals"]),
            "desktop_surface_bundles": int((plugin_dir / "desktop" / "plugin.js").is_file()),
            "declared_deps_without_upper_bound": len(deps["declared_without_upper_bound"]),
            "label": "OBSERVED (static)",
        },
    }
    if a.hermes_tree:
        hs = hermes_static_checks(a.hermes_tree.resolve(), plugin_dir, manifest, recorded)
        if a.context_methods_out:
            a.context_methods_out.write_text(json.dumps(hs["_context_methods"]))
        hs.pop("_context_methods")
        out["hermes_static_validate_subchecks"] = dict(hs, label="OBSERVED (hermes check functions at the hermes tree's HEAD; capability probe excluded)")
    print(json.dumps(out, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
