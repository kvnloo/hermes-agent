# Included-config preservation: existing owner validation

Current main `46d7718a52ff33accb15dc0501736fbdb6833cab` reproduces **8 pass / 2 fail**.
The prepare string from aortegamel's existing `88422bc186024bf6ed9e50223c58d67eaf4cc1c2`
passes **10 / 10** real cases and **3 / 3** original adjacent mocked cases.
This branch contains evidence only. No production implementation was recreated.

See [receipt.json](receipt.json) for scope, provenance, commands, diagnosis, credits and
limitations. The original fixture is reused from `98ea457a`; only the Vitest adapter
import and the obsolete unmerged-wrapper warning assertion change. All preservation,
normal-install, source-copy and genuine-failure assertions remain.

## Reproduce

From the repository root, after fetching the evidence and existing owner commits:

```sh
git fetch origin dot/hermes/135279-real-hooks-evidence
git fetch https://github.com/aortegamel/hermes-agent.git fix/prepare-custom-hooks-failure
# Use a NEW disposable directory; this does not install project dependencies.
export PROBE_ROOT="$(mktemp -d)"
mkdir -p "$PROBE_ROOT/home" "$PROBE_ROOT/tools"
(cd "$PROBE_ROOT/tools" && HOME="$PROBE_ROOT/home" npm install --ignore-scripts --no-audit --no-fund --save-exact lefthook@2.1.14)
python - <<'PY'
import os, pathlib, subprocess
root = pathlib.Path(os.environ['PROBE_ROOT'])
def show(ref, path):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], text=True)
harness = show('98ea457a26852fb4c318bca51c5c308b7500994e', 'tests-js/prepare-hooks-real.test.mjs')
harness = harness.replace("from 'vitest'", "from './node-test-adapter.mjs'")
harness = harness.replace('    expect(result.stderr).toMatch(/lefthook install failed.*continuing without git hooks/)\n', '')
adapter = pathlib.Path('tests-js/evidence/prepare-hooks-owner/node-test-adapter.mjs').read_text()
for name, ref in [('main', '46d7718a52ff33accb15dc0501736fbdb6833cab'), ('owner', '88422bc186024bf6ed9e50223c58d67eaf4cc1c2')]:
    folder = root / name
    (folder / 'tests-js').mkdir(parents=True)
    (folder / 'package.json').write_text(show(ref, 'package.json'))
    (folder / 'tests-js/prepare-hooks-real.test.mjs').write_text(harness)
    (folder / 'tests-js/node-test-adapter.mjs').write_text(adapter)
owner_test = show('88422bc186024bf6ed9e50223c58d67eaf4cc1c2', 'tests-js/prepare-hooks.test.mjs')
(root / 'owner/tests-js/prepare-hooks.test.mjs').write_text(owner_test.replace("from 'vitest'", "from './node-test-adapter.mjs'"))
PY
export PATH="$PROBE_ROOT/tools/node_modules/.bin:$PATH"
export HOME="$PROBE_ROOT/home"
node --test --test-reporter=tap "$PROBE_ROOT/main/tests-js/prepare-hooks-real.test.mjs"
# Expected: exit 1, 8 pass / 2 fail. Continue even though this negative control fails.
node --test --test-reporter=tap "$PROBE_ROOT/owner/tests-js/prepare-hooks-real.test.mjs"
# Expected: exit 0, 10 pass.
node --test --test-reporter=tap "$PROBE_ROOT/owner/tests-js/prepare-hooks.test.mjs"
# Expected: exit 0, 3 pass (owner's original mocked tests).
```

The real tests use an environment allowlist, disposable config files and real linked
worktrees. Neither flags that force hook replacement nor flags that reset hooksPath
are used. Missing Git/npm/Lefthook fails the tests. `diagnosis.json` independently
records scoped versus effective Git queries, config/hook hashes and the real rename.

The existing owner implementation has not been cherry-picked. Owner coordination
was blocked by posting authorization; the ready-to-post note is in the receipt.
No new upstream PR, production change, merge or promotion is part of this evidence.

## Whitespace-only follow-up

Recovered evidence was published first at `229a7e4a4d6f6aa7ccc4bc647e72443e811d7d12`.
See [presence-refinement.receipt.json](presence-refinement.receipt.json) for the
new two-case real regression, RED on owner 88422bc186 (0/2), GREEN with a
one-expression key-presence refinement in a disposable manifest (2/2), and
13/13 original real plus owner-adjacent checks with that refinement.
The production package remains untouched; aortegamel retains implementation
ownership. Upstream coordination is still blocked by posting authorization.

Run the focused test using the `PREPARE_PACKAGE` command in the new receipt.
The receipt gives the exact temporary guard replacement, preserving all other
owner behavior. No new upstream PR or competing production fix was created.
