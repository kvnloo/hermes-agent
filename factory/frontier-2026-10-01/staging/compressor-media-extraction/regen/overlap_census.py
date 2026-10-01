#!/usr/bin/env python3
"""Read-only overlap census for staging/compressor-media-extraction.

For every open NousResearch/hermes-agent PR whose diff touches agent/context_compressor.py:
  * rebuild the PR's own pre-image of the facade (reverse-apply the PR's patch to the head blob;
    fall back to the merge-base blob when GitHub omits the patch);
  * compare each of the 16 moved top-level statements (with attached comments, same segment rule
    as regen/extract_media.py) between pre-image, head and main -> "edits a moved statement" when
    the head text differs from both the pre-image and main (a stale base that already carries
    main's exact text is not an edit);
  * collect Name loads of the 10 moved names the facade does NOT import back, outside the moved
    statements, new in head vs pre-image                     -> "new facade reference" (would be a
    NameError after a textually clean merge with the branch);
  * for the PR's other changed .py files whose added lines mention a moved name, compare old-path
    references (from agent.context_compressor import <moved>, "agent.context_compressor.<moved>"
    strings, context_compressor.<moved> attributes) between pre-image and head, leaving out
    references main already has (the branch rewrites those).
Only GitHub REST/GraphQL reads; nothing touches a local git object store.

    OVERLAP_MAIN=<upstream main sha> OVERLAP_CACHE=<dir> python3 overlap_census.py <regen-dir> census.json open.jsonl [more.jsonl ...]
    python3 overlap_summary.py census.json
"""
import ast, base64, json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import os
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))  # regen/ dir (for extract_media.py)
import extract_media as EM  # noqa: E402

REPO = "NousResearch/hermes-agent"
FACADE = "agent/context_compressor.py"
MOVED = list(EM.MOVED)
FACADE_IMPORTS = {"_is_image_part", "_retire_stale_tool_result_images", "_rewritten",
                  "_strip_historical_media", "_strip_images_from_tool_msg", "_summary_part_text"}
NOT_IMPORTED = set(MOVED) - FACADE_IMPORTS
BRANCH_TOUCHED = ["agent/context_compressor.py", "agent/turn_request_assembly.py", "agent/chat_completion_helpers.py",
                  "agent/image_eviction_policy.py", "tests/agent/test_image_eviction_policy.py",
                  "tests/agent/test_compressor_historical_media.py", "tests/agent/test_compressor_stale_tool_images.py",
                  "tests/agent/test_outbound_stale_vision.py", "tests/agent/test_protected_tail_pressure.py"]
CACHE = Path(os.environ.get("OVERLAP_CACHE", "overlap-cache")).resolve()
CACHE.mkdir(exist_ok=True)
MOVED_RX = re.compile(r"\b(" + "|".join(map(re.escape, MOVED)) + r")\b")


def gh(args, raw=False, tries=6):
    i = 0
    while i < tries:
        p = subprocess.run(["gh", "api"] + args, capture_output=True, text=True, timeout=180)
        if p.returncode == 0:
            return p.stdout if raw else json.loads(p.stdout)
        if "rate limit" in p.stderr.lower():  # shared token: wait for the window instead of failing
            time.sleep(60)
            continue
        if "404" in p.stderr or "Not Found" in p.stderr:
            return None
        if "HTTP 422" in p.stderr:  # e.g. "Sorry, there was a problem generating this diff"
            return {"__http_422__": p.stderr.strip()[:200]}
        i += 1
        time.sleep(4 * i)
    raise RuntimeError(f"gh {args} failed: {p.stderr[:300]}")


def cached(key, fn):
    f = CACHE / (re.sub(r"[^A-Za-z0-9_.-]", "_", key))
    if f.exists():
        return json.loads(f.read_text())
    v = fn()
    f.write_text(json.dumps(v))
    return v


def pr_files(n):
    def fetch():
        out = []
        for page in range(1, 31):
            batch = gh([f"repos/{REPO}/pulls/{n}/files?per_page=100&page={page}"])
            if isinstance(batch, dict):
                return None  # GitHub cannot generate this PR's diff (HTTP 422)
            if not batch:
                break
            out += [{"filename": b["filename"], "status": b["status"], "patch": b.get("patch"),
                     "previous_filename": b.get("previous_filename")} for b in batch]
            if len(batch) < 100:
                break
        return out
    return cached(f"files-{n}", fetch)


def blob_at(path, ref):
    def fetch():
        r = gh(["-H", "Accept: application/vnd.github.raw+json", f"repos/{REPO}/contents/{path}?ref={ref}"], raw=True)
        return r
    return cached(f"blob-{ref}-{path}", fetch)


def merge_base(n, head):
    def fetch():
        pr = gh([f"repos/{REPO}/pulls/{n}"])
        c = gh([f"repos/{REPO}/compare/{pr['base']['sha']}...{head}?per_page=1"])
        return c["merge_base_commit"]["sha"]
    return cached(f"mb-{n}-{head}", fetch)


MAIN = os.environ.get("OVERLAP_MAIN", "")  # exact upstream main SHA the census compares against
_MAIN_FACADE = []


def main_facade():
    if not _MAIN_FACADE:
        if not MAIN:
            raise SystemExit("set OVERLAP_MAIN to the upstream main SHA")
        _MAIN_FACADE.append(segments(blob_at(FACADE, MAIN)))
    return _MAIN_FACADE[0]


HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def reverse_apply(head_text, patch):
    """Return the pre-image of head_text under a unified-diff patch, or None if context mismatches."""
    head = head_text.split("\n")
    hunks = []
    cur = None
    for line in patch.split("\n"):
        m = HUNK.match(line)
        if m:
            cur = {"new_start": int(m.group(3)), "new_len": int(m.group(4) if m.group(4) is not None else 1),
                   "old": [], "new": []}
            hunks.append(cur)
            continue
        if cur is None or line.startswith("\\"):
            continue
        tag, body = (line[:1], line[1:]) if line else (" ", "")
        if tag in (" ", "-"):
            cur["old"].append(body)
        if tag in (" ", "+"):
            cur["new"].append(body)
    for h in reversed(hunks):
        s = h["new_start"] - 1 if h["new_len"] else h["new_start"]
        if head[s:s + len(h["new"])] != h["new"]:
            return None
        head[s:s + len(h["new"])] = h["old"]
    return "\n".join(head)


def segments(src):
    """name -> list of segment texts (with attached comments) for top-level bindings of moved names."""
    lines = src.splitlines(keepends=True)
    tree = ast.parse(src)
    out, moved_nodes = {}, []
    for node in tree.body:
        name = EM._bound_name(node)
        if name in MOVED:
            s, e = EM._segment(lines, node)
            out.setdefault(name, []).append("".join(lines[s:e + 1]))
            moved_nodes.append(node)
    return tree, out, moved_nodes


def facade_refs(tree, moved_nodes):
    ids = {id(n) for n in moved_nodes}
    refs = {}
    for top in tree.body:
        if id(top) in ids:
            continue
        for n in ast.walk(top):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in NOT_IMPORTED:
                refs[n.id] = refs.get(n.id, 0) + 1
    return refs


def old_path_refs(src):
    found = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {"<unparseable>"}
    aliases = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module in ("agent.context_compressor",) :
            for a in n.names:
                if a.name in MOVED:
                    found.add(f"import:{a.name}")
        if isinstance(n, ast.ImportFrom) and n.module == "agent" :
            for a in n.names:
                if a.name == "context_compressor":
                    aliases.add(a.asname or a.name)
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == "agent.context_compressor":
                    aliases.add(a.asname or "agent.context_compressor")
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            for m in re.finditer(r"context_compressor\.(\w+)", n.value):
                if m.group(1) in MOVED:
                    found.add(f"string:{m.group(1)}")
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and n.attr in MOVED:
            v = n.value
            dotted = ast.unparse(v)
            if dotted in aliases or dotted.endswith("context_compressor"):
                found.add(f"attr:{n.attr}")
    return found


def analyse(meta):
    n, head = meta["number"], meta["headRefOid"]
    rec = {"number": n, "head": head, "author": (meta.get("author") or {}).get("login"),
           "updatedAt": meta["updatedAt"], "labels": meta.get("labels", []), "isDraft": meta.get("isDraft"),
           "baseRefName": meta.get("baseRefName")}
    files = pr_files(n)
    if files is None:
        rec["error"] = "file list unavailable: GitHub HTTP 422 (cannot generate the diff)"
        return rec
    rec["n_files"] = len(files)
    fac = [f for f in files if f["filename"] == FACADE or f.get("previous_filename") == FACADE]
    rec["touches_facade"] = bool(fac)
    rec["touches_branch_files"] = sorted({f["filename"] for f in files if f["filename"] in BRANCH_TOUCHED})
    rec["adds_media_module"] = any(f["filename"] == "agent/context_compressor_media.py" for f in files)
    # lines the branch rewrites outside the facade: the context_compressor import / docstring mentions
    touch = []
    for g in files:
        if g["filename"] in BRANCH_TOUCHED and g["filename"] != FACADE:
            for l in (g.get("patch") or "").split("\n"):
                if l[:1] in "+-" and "context_compressor" in l and MOVED_RX.search(l):
                    touch.append(g["filename"]); break
    rec["edits_branch_rewritten_lines"] = sorted(set(touch))
    if not fac:
        return rec
    f = fac[0]
    if f["status"] == "removed" or f["filename"] != FACADE:
        rec["facade_status"] = f["status"]
        rec["edits_moved"] = ["<facade removed or renamed>"]
        return rec
    head_src = blob_at(FACADE, head)
    if head_src is None:
        rec["error"] = "head blob unavailable"
        return rec
    pre = None
    if f["status"] == "added":
        pre = ""
    elif f.get("patch"):
        pre = reverse_apply(head_src, f["patch"])
        rec["preimage"] = "reverse-patch" if pre is not None else "reverse-patch-mismatch"
    if pre is None:
        mb = merge_base(n, head)
        pre = blob_at(FACADE, mb) or ""
        rec["preimage"] = f"merge-base {mb[:10]}"
    try:
        htree, hseg, hnodes = segments(head_src)
    except (SyntaxError, ValueError) as e:
        rec["error"] = f"head unparseable: {e}"
        rec["head_facade_bytes"] = len(head_src.encode())
        rec["head_facade_lines"] = head_src.count("\n")
        return rec
    try:
        ptree, pseg, pnodes = segments(pre) if pre else (ast.parse(""), {}, [])
    except (SyntaxError, ValueError) as e:
        rec["error"] = f"pre-image unparseable: {e}"
        return rec
    edits, carried = [], []
    _, mseg, _ = main_facade()
    for name in MOVED:
        a, b = pseg.get(name), hseg.get(name)
        if a == b:
            continue
        if b == mseg.get(name):
            # the PR's diff touches it only because its base is older than main and its head
            # already holds main's exact text (stale base); nothing to port
            carried.append(name)
            continue
        if a and not b:
            edits.append(f"{name}:removed")
        elif b and not a:
            edits.append(f"{name}:added")
        elif len(b) > 1:
            edits.append(f"{name}:duplicated")
        else:
            edits.append(f"{name}:modified")
    rec["edits_moved"] = edits
    rec["carries_main_text_only"] = carried
    rec["moved_present_in_preimage"] = sorted(pseg)
    pr_refs, h_refs = facade_refs(ptree, pnodes), facade_refs(htree, hnodes)
    rec["new_facade_refs"] = sorted(k for k in h_refs if h_refs[k] > pr_refs.get(k, 0))
    # other python files whose added lines mention a moved name
    other, other_carried = [], []
    nopatch = [g for g in files if g["filename"].endswith(".py") and g["filename"] != FACADE
               and g["status"] != "removed" and g.get("patch") is None]
    if len(nopatch) > 50:  # mega-diff (usually a merge of main): do not fetch hundreds of blobs
        rec["other_files_scan"] = f"skipped: {len(nopatch)} changed .py files have no patch"
        rec["other_files_new_old_path_refs"] = []
        return rec
    for g in files:
        if g["filename"] == FACADE or not g["filename"].endswith(".py") or g["status"] == "removed":
            continue
        added = "\n".join(l[1:] for l in (g.get("patch") or "").split("\n") if l.startswith("+"))
        if g.get("patch") is not None and not MOVED_RX.search(added):
            continue
        hs = blob_at(g["filename"], head)
        if hs is None:
            continue
        if not old_path_refs(hs):  # nothing at head, so nothing new
            continue
        if g["status"] == "added":
            ps = ""
        else:
            ps = reverse_apply(hs, g["patch"]) if g.get("patch") else None
            if ps is None:
                ps = blob_at(g.get("previous_filename") or g["filename"], merge_base(n, head)) or ""
        ms = blob_at(g["filename"], MAIN)
        main_refs = old_path_refs(ms) if ms else set()
        added_refs = old_path_refs(hs) - old_path_refs(ps)
        if added_refs & main_refs:
            # the PR carries a line main already has; the branch rewrites that line on main
            other_carried.append({"file": g["filename"], "carries_main_old_path_refs": sorted(added_refs & main_refs)})
        new = sorted(added_refs - main_refs)
        if new:
            breaks = sorted(x for x in new if x.split(":", 1)[-1] not in FACADE_IMPORTS)
            other.append({"file": g["filename"], "new_old_path_refs": new,
                          "breaks_after_merge": breaks,
                          "resolves_via_facade_import_gate_only": sorted(set(new) - set(breaks))})
    rec["other_files_new_old_path_refs"] = other
    rec["other_files_carry_main_lines"] = other_carried
    return rec


def main():
    regen_dir, out = sys.argv[1], sys.argv[2]
    metas = {}
    for fn in sys.argv[3:]:
        for line in open(fn):
            m = json.loads(line)
            metas[m["number"]] = m
    targets = []
    truncated = []
    for m in metas.values():
        if not m.get("files"):  # GraphQL returns files=null for some PRs (diff too large); list them via REST
            truncated.append(m)
            continue
        paths = [x["path"] for x in m["files"]["nodes"]]
        if FACADE in paths or "agent/context_compressor_media.py" in paths:
            targets.append(m)
        elif m["files"]["pageInfo"]["hasNextPage"]:
            truncated.append(m)
    print(f"open PRs scanned: {len(metas)}; facade in first 100 paths: {len(targets)}; truncated or null lists to check via REST: {len(truncated)}", flush=True)
    with ThreadPoolExecutor(6) as ex:
        res_t = list(ex.map(lambda m: (m, pr_files(m["number"])), truncated))
    unavailable = [m for m, files in res_t if files is None]
    targets += unavailable  # analyse() records them as errors instead of guessing
    for m, files in res_t:
        if files is None:
            continue
        if any(f["filename"] in (FACADE, "agent/context_compressor_media.py") or f.get("previous_filename") == FACADE for f in files):
            targets.append(m)
    print(f"targets after truncated-list check: {len(targets)}", flush=True)
    with ThreadPoolExecutor(6) as ex:
        recs = list(ex.map(analyse, sorted(targets, key=lambda m: m["number"])))
    json.dump({"scanned": len(metas), "truncated_checked": len(truncated),
               "truncated_numbers": sorted(m["number"] for m in truncated), "records": recs}, open(out, "w"), indent=1)
    print("done", len(recs))


if __name__ == "__main__":
    main()
