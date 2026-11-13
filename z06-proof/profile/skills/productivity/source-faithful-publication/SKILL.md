---
name: source-faithful-publication
description: Use when vault and repo disagree on the current document.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [documents, vault, publication, resume]
    related_skills: [obsidian, pdf, docx, github]
---

# Source-faithful publication

## When to Use

A notes-vault folder and one or more repos all claim to hold the current resume, CV, portfolio, or similar personal document, and the job is to decide what may be published. Extraction quirks are in `references/extraction.md`.

## Always

- If the user asked for a plan only, stop after the authority map. Do not copy, commit, or push.
- Copy the vault folder into a work directory. Do not edit the vault unless asked.
- Do not rsync a vault folder onto a repo. Map files. Keep repo-only assets. Drop Word lock files (`~$*`) and logs that are not the document.
- Leave an archive repo untouched when the user says it stays an archive.
- Do not add a number, skill, date, title, or contact detail that is absent from a source document. A later rewrite is not newer if its distinctive numbers are missing from the designed source.
- Wording, dates, and generated files are separate authorities. Name each before writing. A plaintext export can be behind the designed file; a generated PDF or LaTeX file can invent claims the design never made.
- An index note that names files "most up to date" can point at old exports. Check the designed file, not the index.
- Publishing the designed document publishes the contact block on it. If the public copy currently uses placeholders, say that the real contact will become public before the push.
- After a rewrite, extract the new PDFs and confirm banned strings (placeholder email, invented percents) are absent and required source strings are present.

## Procedure

1. Resolve the vault. `OBSIDIAN_VAULT_PATH` may be unset and `~/Documents/Obsidian Vault` may not exist. Read `~/.config/obsidian/obsidian.json` and use the vault marked open. Pass the concrete absolute path to file tools.
2. List the document folder by name and mtime only. Do not read the rest of the vault. Ignore older same-named files outside that folder.
3. Find every candidate repo (`gh search repos`, `gh api user/repos`). A repo named for the document and a later maintained repo can both exist. The maintained one is not automatically the factual source.
4. Copy the folder to a work directory, excluding `~$*` and unrelated logs. Clone the destination repo beside it. Do not work inside the vault.
5. Extract text with the file-type skill, then compare claims, not line sets. See `references/extraction.md`.
6. Write the publication from the authority split:
   - current wording from the newest designed source (odt or equivalent), not from a stale plaintext export
   - dates from the file that actually states them, when that file is not contradicted by the design
   - older bullets only when a source has them; a title with no bullets stays a title
7. Rebuild generated PDFs from the reconciled sources. Do not leave old generated PDFs in the repo if they still contain claims you removed.
8. Push only the destination the user named. Verify the remote commit sha after the push.

## Compile note

Jake-style resumes often `\input{glyphtounicode}` and set `\pdfgentounicode=1`. Those are pdfTeX-only. On XeTeX, drop both lines; XeTeX already emits Unicode. Do not treat a missing engine as a reason to publish the old PDF.
