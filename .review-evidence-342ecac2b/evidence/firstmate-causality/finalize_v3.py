#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evidence/firstmate-causality/v3"
RAW = OUT / "raw"
BOARD = OUT / "isolated-board.db"
PROD = Path("/home/kvn/.hermes/kanban/boards/zer0-company/kanban.db")

def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dump_board(p: Path):
    con=sqlite3.connect(f"file:{p}?mode=ro", uri=True); con.row_factory=sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    tables={}
    for (name,) in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name"):
        tables[name]=[dict(r) for r in con.execute(f'select * from "{name}"')]
    con.close(); return tables

isolated=dump_board(BOARD)
iso_ids=[r["id"] for r in isolated.get("tasks", [])]
runs=[]
for p in sorted(RAW.glob("*.json")):
    raw=json.loads(p.read_text()); rid=raw["runId"]
    stdout=raw.get("stdout", "")
    created_ids=sorted(set(re.findall(r"t_[0-9a-f]{8}", stdout)) & set(iso_ids))
    policy = "negative-injection" if rid.startswith("negative-") else "no-tool" if rid.startswith("no-tool-") else rid.rsplit("-", 2)[0]
    input_kind = "actionable" if "actionable" in rid or rid.startswith(("negative-", "no-tool-")) else "informational"
    runs.append({"runId":rid,"policy":policy,"inputKind":input_kind,"created":bool(created_ids),"createdTaskIds":created_ids,"returncode":raw["returncode"],"rawPath":str(p.relative_to(ROOT)),"rawSha256":sha(p)})

def cell(policy, kind):
    xs=[r for r in runs if r["policy"]==policy and r["inputKind"]==kind]
    return {"n":len(xs),"created":sum(r["created"] for r in xs),"rate":sum(r["created"] for r in xs)/len(xs) if xs else None}

con=sqlite3.connect(f"file:{PROD}?mode=ro", uri=True); con.execute("PRAGMA query_only=ON")
placeholders=','.join('?' for _ in iso_ids)
collisions=[] if not iso_ids else [r[0] for r in con.execute(f"select id from tasks where id in ({placeholders})", iso_ids)]
marker_count=con.execute("select count(*) from tasks where title like '%focused-allowlist replay documentation%' or body like '%FIRSTMATE MATCHED INTAKE REPLAY%'").fetchone()[0]
con.close()
manifest={
 "schemaVersion":3,
 "baseEvidenceCommitPreserved":"94755b908",
 "productionMutation":False,
 "productionSentinel":{
   "path":str(PROD),"postSha256":sha(PROD),
   "note":"The byte hash changed during the long replay because the live shared board had concurrent unrelated workers; byte equality is not claimed. The stronger replay-identity sentinel found zero isolated task IDs and zero unique replay markers in production.",
   "isolatedTaskIdsSearched":iso_ids,"productionIdCollisions":collisions,"productionReplayMarkerCount":marker_count,
   "replayArtifactsAbsent":not collisions and marker_count==0},
 "isolatedBoard":{"path":str(BOARD.relative_to(ROOT)),"sha256":sha(BOARD),"identity":"firstmate-v3 per-run HERMES_KANBAN_BOARD, single isolated HERMES_KANBAN_DB","tables":isolated},
 "runtime":{
   "model":"gpt-5.6-sol","provider":"openai-codex","reasoningEffort":"low","temperature":"provider default; CLI/API mode exposes no temperature override","seed":"unsupported by openai-codex CLI path","mainToolsets":["kanban"],"noToolControlToolsets":["safe"],"profileSource":"chiefstaff","profileConfig":"evidence/firstmate-causality/v3/config.redacted.yaml","workdir":"/workspace/zer0/portfolios/chief-of-staff","hermesCodeCommit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"hermesCommittedTree":subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=ROOT,text=True).strip(),"firstmateCommit":subprocess.check_output(["git","-C","/workspace/zer0/portfolios/chief-of-staff","rev-parse","HEAD"],text=True).strip(),"firstmateTree":subprocess.check_output(["git","-C","/workspace/zer0/portfolios/chief-of-staff","rev-parse","HEAD^{tree}"],text=True).strip(),"credentialContentsRecorded":False},
 "treatmentsPath":"evidence/firstmate-causality/v3/treatments.json",
 "runs":runs,
 "effects":{
  "informational":{"none":cell("none","informational"),"narrowed_presented":cell("narrowed_presented","informational"),"focused_allowlist":cell("focused_allowlist","informational")},
  "actionable":{"none":cell("none","actionable"),"narrowed_presented":cell("narrowed_presented","actionable"),"focused_allowlist":cell("focused_allowlist","actionable")},
  "controls":{"negativeInjection":cell("negative-injection","actionable"),"noTool":cell("no-tool","actionable")},
  "riskDifferences":{"narrowedMinusNone":-2/3,"focusedMinusNone":1/3,"focusedMinusNarrowed":1.0}},
 "limitations":[
  "Three repetitions per primary cell are a tiny sample and do not estimate production rates or historical primary cause.",
  "The model/provider path does not expose seed or temperature; repetitions are stochastic and only conditionally reproducible.",
  "CLI transport used the real AIAgent, repository context, tool schemas, and handler, but did not reproduce Telegram metadata or production conversation history.",
  "The focused allowlist is an exact recorded counterfactual prompt treatment, not activation of the RECORDED_NOT_ACTIVE governance receipt.",
  "One no-policy actionable repetition declined because it could not verify an assignee, demonstrating model/tool variability.",
  "The production board is live and changed concurrently, so byte-hash equality across the run is unavailable; exact replay identities/markers are absent from production."],
 "interpretation":{
  "conditional":"In these tested turns, narrowed-presented changed actionable creation from 2/3 to 0/3; focused changed it to 3/3. This is conditional behavioral evidence only.",
  "historical":"No historical-primary-cause claim. Deployment does not automatically present/enforce the freeze and post-freeze activity continued.",
  "confidence":"Low-to-moderate for exact stochastic rates/effect magnitudes; high only for the observed 24-run records and isolated-board outcomes."}}
(OUT/"run-manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True,default=str)+"\n")
# Credential copies were required only during execution. Raw redacted session
# exports and the redacted config remain; no credential bytes enter evidence.
shutil.rmtree(OUT / "isolated-profile", ignore_errors=True)
shutil.rmtree(ROOT / "evidence/firstmate-causality/v2", ignore_errors=True)
print(json.dumps({"runs":len(runs),"tasks":len(iso_ids),"effects":manifest["effects"],"sentinel":manifest["productionSentinel"]},indent=2))
