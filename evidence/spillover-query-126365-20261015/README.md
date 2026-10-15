# LIMITED: spillover query semantics at PR #126365

This is downstream evidence preservation only. It is not an implementation,
merge-readiness verdict, native Windows reproduction, or origin-action claim.

## Recorded result

At exact origin head `77dcd5879a51815e3c05382fb38f65ea583f0245`, a standalone
Python/sqlite3/re diagnostic executed the source's extracted query and regex
literals against 30 synthetic in-memory fixtures. Both SQL paths selected the
same 10 rows; the reference query extracted 10 unique names.

| Fixture group | Cases | Reference SQL | Capture SQL | Regex finds names | Target found after SQL |
|---|---:|---:|---:|---:|---:|
| Forward-slash POSIX / Windows, raw / JSON string, either column | 8 | 8 | 8 | 8 | 8 |
| Windows drive / UNC backslash, raw / JSON string, either column | 8 | 0 | 0 | 0 | 0 |
| Other directory / no path negative controls | 8 | 0 | 0 | 0 | 0 |
| Backslash target plus forward-slash control in other column | 2 | 2 | 2 | 2 | 0 |
| NUL-prefixed structured content, forward slash | 2 | 0 | 0 | 2 | 0 |
| NUL-prefixed structured content, backslash | 2 | 0 | 0 | 0 | 0 |

The backslash targets remain absent even when the other column admits the row.
The NUL-prefixed content result is a separate representation boundary observed
with SQLite 3.53.1, not a claim about all producers or SQLite versions.

Recorded environment: Linux x86_64, Python 3.12.14, SQLite 3.53.1. Recorded
command: `python diagnostic.py > diagnostic_output.txt`; assertions passed.
An independent reviewer attested at 2026-10-15 14:28:52 UTC that one isolated
rerun (`python -I -B diagnostic.py`) reproduced all results byte-for-byte, with
the original manifest unchanged. This is a coordinator-delivered reviewer
attestation; the reviewer checked saved provenance without a new GitHub refetch.
The producer and independent artifact copies have identical script, results,
stdout, and provenance hashes.
This packaging pass only compared existing bytes and parsed recorded data. It
did not rerun the diagnostic or execute a Hermes test.

## Meaning and limits

The SQL patterns and regex contain the forward-slash path segment `spillover/`. The
pinned source builds paths using host `Path` operations and interpolates the
returned string into the notice. Together these support a source-inferred
Windows-backslash reference-discovery gap. They do not establish actual Hermes
persistence behavior, native Windows execution, file lifetime or deletion.

No Hermes imports, repository suite, cleanup functions, session deletion,
provider calls, real databases, archives, or production data were executed.
`DELETE FROM messages` in the diagnostic touches only an in-memory synthetic
table. There is no repair in this packet. The already-repaired mtime/session-
lifetime case is not reopened. Current-head maintainer tests are reported
evidence, not results produced by this diagnostic. No global worker capacity
or implementation ownership is asserted.

## Freshness and ownership

Read-only refresh on 2026-10-15 at approximately 15:25 UTC found the PR open and
unmerged at the exact tested head. The latest returned comment remains the
author's 13:26:57 UTC confirmation. The returned timeline has 27 entries and
the submitted-review list has eight COMMENTED reviews.

- [Origin PR and stated session-lifetime invariant](https://github.com/NousResearch/hermes-agent/pull/126365)
- [Austin's current-head re-verification](https://github.com/NousResearch/hermes-agent/pull/126365#issuecomment-6193039596)
- [liuhao1024's current-head confirmation](https://github.com/NousResearch/hermes-agent/pull/126365#issuecomment-6193195269)
- [Austin's ownership/mtime verification](https://github.com/NousResearch/hermes-agent/pull/126365#issuecomment-6169164141)

Feature and ownership-linked repair: liuhao1024. Integration, conflict
resolution, verification and test-dependency repair: Austin (austinpickett).
Earlier retention-floor fix: teknium1. This diagnostic claims only the scoped
query/regex observations. Original report credit remains with Froraut; prior
clock-mismatch evidence remains with ehz0ah, Lokee86 and andrexibiza. Synthetic
fixtures alone do not establish a new product requirement or supported-path
impact; native Windows/full-Hermes evidence remains absent.

## Compact preserved artifacts

- `diagnostic.py`: exact executed script, unchanged
- `diagnostic_results.json`: exact recorded per-fixture data and counts
- `diagnostic_output.txt`: exact recorded stdout
- `literal_provenance.json`: exact source URLs, SHA-256 and Git blob SHA-1,
  source-line spans, and extracted literals
- `receipt.json`: concise publication provenance and limits
- `prepare_replay.py`: new input-preparation helper, not executed in this pass
- `SHA256SUMS`: packet hashes

Bulk PR/comment snapshots and duplicated source/API-response files are omitted.
There are no private user records, credentials, contact details, or workspace
paths in the packet. All fixture paths are deliberately synthetic.

## Reproduction inputs

The exact executed script expects source and connector-shaped metadata inputs.
To reconstruct only what it consumes, obtain these four public files at the
pinned commit, preserving their repository-relative paths in a scratch source
directory. `literal_provenance.json` contains their immutable URLs and hashes:

- `tools/tool_result_storage.py`
- `hermes_state_messages.py`
- `hermes_state_maintenance.py`
- `hermes_state.py`

Then use a separate new scratch output directory:

```sh
python prepare_replay.py /path/to/pinned-source /path/to/new-replay-dir
cd /path/to/new-replay-dir
python diagnostic.py > diagnostic_output.txt
```

The helper verifies all four hashes before copying, makes no network requests,
and creates only the metadata fields consumed by the unchanged diagnostic.
Its reconstructed comment metadata preserves the recorded count and latest
link; it is not a fresh GitHub read or a full timeline snapshot. The recorded
result files in this packet are not overwritten. Reproduction on a different
Python/SQLite platform must be labeled as a new run. The preparation helper
has not been executed; review its source before using it.

## Coordination boundary

The canonical registry routes this project to `kvnloo/hermes-agent`. Factory
rules permit downstream-only receipts before origin authorization, require
deduplication by `NousResearch/hermes-agent#126365`, and prohibit unsolicited
account mentions. This packet stays LIMITED. Publication requires independent
packet review and a fresh duplicate/head check. No origin post or default-
branch modification is included.
