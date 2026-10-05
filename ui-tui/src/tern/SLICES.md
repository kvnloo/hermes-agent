# Tern TSP slices

The product branch is `feat/tern-tsp-surface`.

Each slice has its own branch. Test the slice branch. Then combine it into the product branch. Do not rebase the product branch onto upstream.

| Slice | Branch | Commit |
| --- | --- | --- |
| Program features | `feat/tern-tsp-program-features` | `9e07f85f` |
| Change events | `feat/tern-tsp-change-events` | `d144687c` |
| Visible surface | `feat/tern-tsp-visible-surface` | this branch |

Upstream sync uses `sync/tern-tsp-upstream`. Merge upstream into that branch. Then merge that branch into the product branch. Cherry-pick a slice commit if a conflict makes the product branch hard to save.

CI for these branches is `.github/workflows/tern-tsp-slices.yml`. It runs the TSP unit tests. It does not replace the upstream Hermes CI.
