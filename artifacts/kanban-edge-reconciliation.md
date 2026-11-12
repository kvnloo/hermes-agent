# Production Kanban dangling-edge reconciliation manifest

Observed: `2026-08-18T15:12:47.797540+00:00`
Database: `/workspace/hermes-home/kanban/boards/zer0-company/kanban.db`
Identity: device `66307`, inode `413083864`
SQLite user/schema version: `0` / `32`
Input file SHA-256: `c1a3113d806c1e1f25cc3aa8f1d258f88a55cab9791d7da30c881e4878d6ebd3`
Query SHA-256: `42913b70cd1320d4724d370a0ca2ca143c36e441207e250bea165c07bdc13610`

## Read-only proof

- Open mode: `SQLite URI mode=ro`; `PRAGMA query_only=TRUE`.
- Logical sentinel before: `8e6342809d35331c2bb8f91c159d84fbf61550a09e3843a459d9f454659f330b`.
- Logical sentinel after: `8e6342809d35331c2bb8f91c159d84fbf61550a09e3843a459d9f454659f330b`.
- Equal: `True`.
- External post-transaction sentinel equal: `True`.
- Input file SHA-256 after: `c1a3113d806c1e1f25cc3aa8f1d258f88a55cab9791d7da30c881e4878d6ebd3` (equal: `True`).
- No INSERT, UPDATE, DELETE, schema statement, backup, checkpoint, or writable connection is used.

## Fresh counts

- Tasks: **160**
- Dependency edges: **278**
- Dangling edges: **165**
- Missing parent: **0**
- Missing child: **0**
- Both endpoints missing: **165**

## Decision policy

Structural absence is proven only within this exact board snapshot. Cross-board/legacy provenance is UNKNOWN because no provenance registry is present in the canonical database. Every edge therefore defaults to proposed `retain` with low confidence. These are proposals only; this manifest authorizes no mutation.

## Exact query

```sql
SELECT
  l.parent_id,
  l.child_id,
  CASE
    WHEN p.id IS NULL AND c.id IS NULL THEN 'both_missing'
    WHEN p.id IS NULL THEN 'missing_parent'
    WHEN c.id IS NULL THEN 'missing_child'
  END AS structural_class,
  p.id, p.status, p.assignee, p.tenant, p.created_at, p.completed_at,
  c.id, c.status, c.assignee, c.tenant, c.created_at, c.completed_at
FROM task_links AS l
LEFT JOIN tasks AS p ON p.id = l.parent_id
LEFT JOIN tasks AS c ON c.id = l.child_id
WHERE p.id IS NULL OR c.id IS NULL
ORDER BY l.parent_id, l.child_id
```

## Dangling edges

| Parent | Child | Structural class | Surviving endpoint metadata | Provenance | Proposed action | Confidence |
|---|---|---|---|---|---|---|
| `t_020e9422` | `t_93ff8d39` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_038be7f4` | `t_d302884c` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_03c7da05` | `t_0ac56509` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_04032337` | `t_865bad0a` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0407543f` | `t_95dfe859` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_060944fa` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_07a52e57` | `t_994d61ec` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_09ff8bfe` | `t_9f8f695f` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0ac56509` | `t_c69bf3a1` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0af67b33` | `t_72294ce7` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_060944fa` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_2e12c370` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_3b6ac7a1` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_74c56400` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_822dd40f` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_94aa7fa9` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_b001feb8` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_b0d54a15` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_bd0d431b` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_ee7494c5` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_f93b1704` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_0bb55798` | `t_fd01ac9a` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_143d2406` | `t_64e596fa` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_17b5757e` | `t_76cd0fdb` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_198de577` | `t_d62182b4` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_1bf0bd85` | `t_4a9c85a4` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_1bf0bd85` | `t_c92ea301` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_1d878273` | `t_344e7186` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_1f864a5a` | `t_e5406f00` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_28a8c942` | `t_b0d54a15` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_294ea1ab` | `t_653635a9` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_2e12c370` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_316fe5c5` | `t_39bb66dc` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_316fe5c5` | `t_5c3d615e` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_316fe5c5` | `t_fc38bff3` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_32c0799f` | `t_a9f17226` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_39bb66dc` | `t_5c3d615e` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_39bb66dc` | `t_fc38bff3` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_3a18226d` | `t_f52a2bff` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_3a3a68d3` | `t_9f8f695f` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_3b6ac7a1` | `t_28a8c942` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_3b6ac7a1` | `t_63866ca7` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_3b8ecb00` | `t_bdd872d4` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_3da30cb5` | `t_de466b63` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_3da30cb5` | `t_fc0d6ed8` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_43b70b1f` | `t_6bae2df0` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_43e2ee4f` | `t_a0062520` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_45b99df9` | `t_ec3f9f50` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_48eae151` | `t_cb8ee77c` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_4a9c85a4` | `t_69118d5d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_4bd24553` | `t_03c7da05` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_4c95c45a` | `t_e441e77e` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_543fd3ed` | `t_038be7f4` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_543fd3ed` | `t_f8ff812a` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_55966a8d` | `t_653635a9` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_57f3c660` | `t_a0bb1fd7` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_5a8ca981` | `t_0407543f` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_5c3d615e` | `t_1d878273` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_5dbf70cb` | `t_9f8f695f` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_60e85ec5` | `t_b4391477` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_63866ca7` | `t_b0d54a15` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_63866ca7` | `t_c71a99da` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_6483ad3e` | `t_8d379df2` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_64e596fa` | `t_4c95c45a` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_650ff5a4` | `t_aad93dea` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_650ff5a4` | `t_cdc8a72c` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_653635a9` | `t_2ca6b897` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_653635a9` | `t_344e7186` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_653635a9` | `t_3da30cb5` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_653635a9` | `t_45b99df9` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_653635a9` | `t_aad93dea` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_653635a9` | `t_fc0d6ed8` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_65596f9f` | `t_04a67993` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_65596f9f` | `t_d73216d9` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_6bae2df0` | `t_af76e04a` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_6e9bf110` | `t_7b084ccc` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_700f843a` | `t_b0d54a15` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_72294ce7` | `t_401ffc7d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_7432ab2d` | `t_83991e68` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_74c56400` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_76cd0fdb` | `t_04032337` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_7a562d91` | `t_74ff9158` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_7b781285` | `t_b11523ef` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_7da58d22` | `t_8aee0a41` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_7e69a38f` | `t_abf6b6ab` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_7fa9142e` | `t_c389bc1d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_822dd40f` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_865bad0a` | `t_be20d6ea` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_894610bb` | `t_d03fed63` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_8aee0a41` | `t_17b5757e` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_8c206bf1` | `t_f64828dc` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_8c76b22a` | `t_894610bb` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_8df22021` | `t_700f843a` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_8df22021` | `t_e53102ad` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_912db980` | `t_ec2951f0` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_93ff8d39` | `t_98661560` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_94aa7fa9` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_95dfe859` | `t_9ad644b0` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_98661560` | `t_a9ea0808` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_992958ee` | `t_401ffc7d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_9966a8c5` | `t_a2da5d22` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_9ad644b0` | `t_60e85ec5` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_9bba6ec7` | `t_0d9d18ff` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_9bba6ec7` | `t_6b1787e3` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_9d0e1a44` | `t_e141bdd7` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_9e404328` | `t_ef6f2065` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_a0bb1fd7` | `t_7b781285` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_a18c3871` | `t_a21131e6` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_a2da5d22` | `t_b0d54a15` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_a676edae` | `t_6483ad3e` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_a8c65c18` | `t_7a562d91` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_a8c65c18` | `t_a9a97699` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_a9a97699` | `t_74ff9158` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_a9ea0808` | `t_aca3a63a` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_a9f17226` | `t_9d8ff84d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_aa62402d` | `t_28a8c942` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_aa62402d` | `t_63866ca7` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_aad93dea` | `t_80c5ebaa` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_abf6b6ab` | `t_a18c3871` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_abf6b6ab` | `t_aa362077` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_b001feb8` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_b11523ef` | `t_d49e9a9f` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_b3b69de5` | `t_8df22021` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_b3b69de5` | `t_b0d54a15` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_b4391477` | `t_71a2c3a2` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_bd0d431b` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_bdd872d4` | `t_32c0799f` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_c31d1382` | `t_9e404328` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_c71a99da` | `t_b3b69de5` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_cb8ee77c` | `t_7b9a39e3` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_cdc8a72c` | `t_aad93dea` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_d302884c` | `t_020e9422` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_d302884c` | `t_2ca6b897` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_d49e9a9f` | `t_3b8ecb00` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_d62182b4` | `t_e477ebf9` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_da75f570` | `t_038be7f4` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_da75f570` | `t_543fd3ed` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_db2e6a35` | `t_235ade89` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_e141bdd7` | `t_09ff8bfe` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_e141bdd7` | `t_3a3a68d3` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_e141bdd7` | `t_5dbf70cb` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_e441e77e` | `t_7da58d22` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_e477ebf9` | `t_fbce6e26` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_e53102ad` | `t_07a52e57` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_e53102ad` | `t_b0d54a15` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_e73d7498` | `t_653635a9` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_e7739fc3` | `t_1f864a5a` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_ea40d0cb` | `t_3b98ca39` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_ea40d0cb` | `t_8c76b22a` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_ee7494c5` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_ef6f2065` | `t_43e2ee4f` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_f43259a9` | `t_f556db83` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_f52a2bff` | `t_48eae151` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_f556db83` | `t_c92ea301` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_f64828dc` | `t_1a5c2439` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_f64828dc` | `t_f6f697cd` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_f6f697cd` | `t_1a5c2439` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_f93b1704` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_f9a5ab99` | `t_653635a9` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_fbce6e26` | `t_3a18226d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_fc0d6ed8` | `t_61775bad` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_fc38bff3` | `t_5c3d615e` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_fc38bff3` | `t_72d2a46f` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |
| `t_fd01ac9a` | `t_aa62402d` | `both_missing` | none | `UNKNOWN` | `retain` | `low` |

## Governance boundary

Any migration is a separate Captain-approved card requiring a backup, rollback plan, and independent verifier. Blind deletion is explicitly rejected.

## Reproduction

```text
python scripts/kanban_edge_reconciliation.py --db /workspace/hermes-home/kanban/boards/zer0-company/kanban.db --json /workspace/zer0/oss/hermes-agent/.worktrees/t_8d9f6cb0/artifacts/kanban-edge-reconciliation.json --markdown /workspace/zer0/oss/hermes-agent/.worktrees/t_8d9f6cb0/artifacts/kanban-edge-reconciliation.md --seals /workspace/zer0/oss/hermes-agent/.worktrees/t_8d9f6cb0/artifacts/kanban-edge-reconciliation.sha256.json
```
