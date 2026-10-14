# Email inline text attachment review: HOLD

The tested fix works. A separate named-main-body compatibility question remains.

- Origin: [NousResearch/hermes-agent PR138417](https://github.com/NousResearch/hermes-agent/pull/138417), by **rodricksz4h5**; related [issue138416](https://github.com/NousResearch/hermes-agent/issues/138416).
- Exact source head: `126a18a9fe75e1e2e94a6cb090a1bcf37b68b381`.
- Exact base/parent: `0e427d788d253630d38a3a51cd76849e73cd6925`.
- Independent Linux sandbox evidence, 2026-10-14. No production patch is included or claimed here. This packet does not authorize upstream action or change implementation ownership.

## What was verified

Identical files and canonical `scripts/run_tests.sh` selection on the two exact revisions:

| Coverage | Base | Head |
|---|---:|---:|
| 71 pre-existing email controls, five files | 71 passed | 71 passed |
| 3 author regression cases, copied byte-for-byte | 1 passed, 2 failed | 3 passed |
| 11 independently written contract cases | 6 passed, 5 failed | 11 passed |
| Total distinct contract cases | 78 passed, 7 failed | 85 passed |

The independent tests serialize actual MIME bytes, call the real `EmailAdapter._parse_fetched_message`, and use the real document cache in a per-test temporary `HERMES_HOME`. They check plain/HTML body preservation, named inline text/plain, text/html and text/csv files, attachment ordering, quoted and RFC2231 filenames, exact cached bytes/MIME/type metadata/counts, unnamed inline body controls, existing explicit attachments, skip-attachments behavior, and an unnamed inline CSV control. Parser/cache functions are not replaced. Repeated qualification runs add no distinct coverage.

## Compatibility HOLD: named inline main text

The separate `test_email_named_body_characterization.py` is an observation recorder, **not a passing product-contract assertion**, and is excluded from the 85-case count. Its exact serialized fixture is `named-inline-body.eml` (SHA256 `4400dc9d94b2b10523392d777369998f845714a103e1cc612e338bd8a781d0b1`).

The multipart message contains inline main text with `filename="message.txt"`, followed by a CSV attachment:

- Base body: `Please calculate the total from the attached data.\n`; only `data.csv` cached.
- Head body: empty; `message.txt` and `data.csv` cached.

The instructions are **removed from the parsed body and reclassified as a cached file**, not deleted. [RFC2183 sections2.1 and2.3](https://www.rfc-editor.org/rfc/rfc2183.html#section-2.3) permit a normally displayed inline entity to carry a filename; a filename does not itself require separate-file treatment. This establishes a valid MIME compatibility concern, not a claim that a particular client sent this shape in production.

One narrow design decision remains with the owner/maintainers: should an inline text part with a filename always be excluded from the parsed body, including when it is the message's sole textual body, or should that body case retain its instructions? The targeted green cases do not settle that choice. No maintainer rejection or acceptance is claimed.

## Requirement evidence and limits

The pinned [email documentation](https://github.com/NousResearch/hermes-agent/blob/0e427d788d253630d38a3a51cd76849e73cd6925/website/docs/user-guide/messaging/email.md#receiving-messages) documents local attachment caching and HTML-only body extraction; its skip-attachments section says the body remains processed. The existing implementation/tests establish separate body and cached-file paths. The source issue expressly reports a synthetic EmailMessage reproducer, **not a live Apple/iOS Mail capture**. RFC2183 makes the named-body semantic risk concrete but does not define Hermes's preferred product policy.

Not demonstrated: live mail-client output, IMAP/SMTP transport, real accounts/credentials, complete dispatch/agent lifecycle, all MIME nesting/case variants, full suite, hosted CI, performance or merge readiness. No i18n, IPC or isolation changes were made. Only focused email files ran; no production code was changed.

## Runtime and provenance

The existing PM-built Python3.14.7 and test environment were reused without dependency installation or environment mutation. This is **not a fresh install**. Its editable metadata points to an earlier checkout; the canonical runner's supported `HERMES_PYTHON` path was used. The exact runner, root `pyproject.toml`/`uv.lock`, and manager manifests match the qualified environment. All 90 installed distribution/version pairs match the lock after name normalization.

The review plugin records all loaded repository-module paths at per-file process end, rejects imports from the reused environment's foreign editable source, and asserts the email adapter resolves from the intended checkout. All final per-file receipts have no foreign source imports. Source hashes distinguish exact base from head. Published path placeholders replace sandbox roots only; module-relative paths and hashes remain intact. Each run used a fresh disposable HOME; canonical test fixtures also isolate `HERMES_HOME`. Runtime binaries, dependencies and source object stores are not embedded.

## Reproduction

Use a disposable checkout with both exact commits available and a lock-qualified PM test interpreter. `replay.sh CHECKOUT TEST_PYTHON OUTPUT_DIR` copies this packet's three test files and read-only provenance plugin into the disposable checkout, then runs the identical focused selection and separate observation at base and head. It makes no downloads or dependency changes. It refuses tracked modifications and never force-checks out. The base's seven expected failures are part of the comparison; review the logs rather than interpreting the shell script's completion as a product verdict.

`origin_test_email_inline_text_attachment.py` preserves the author's test source exactly; replay uses the distinct filename `test_email_inline_origin_contract.py` on both revisions to avoid counting the head's original file twice. The provenance plugin observes source files for qualification; the contract tests exercise behavior rather than reading production source.
