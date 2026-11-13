---
name: codebase-exploration
description: "Use when exploring codebases to understand purpose."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [codebase, exploration, investigation]
    related_skills: [codebase-inspection, github]
---

# Codebase Exploration

Explore unfamiliar codebases to understand purpose and structure.

## When to Use

- User asks to "look through" or "examine" a repository or codebase
- User wants to understand what a project does or how it works
- User needs to familiarize themselves with an unfamiliar codebase
- User asks "what is this code for?" or "how does this work?"
- Before making changes to an unfamiliar codebase
- When assessing a third-party library or tool

## Prerequisites

No specific tools required - uses standard shell commands (ls, find, grep, head, etc.)

## 1. Initial Survey

```bash
# List top-level contents with details
ls -la

# Look for README or documentation files
find . -maxdepth 1 -type f \( -name "README*" -o -name "INSTALL*" -o -name "LICENSE*" -o -name "CHANGELOG*" -o -name "CONTRIBUTING*" \) 2>/dev/null | head -10

# Check for version control
find . -name ".git" -type d 2>/dev/null
find . -name ".hg" -type d 2>/dev/null
find . -name ".svn" -type d 2>/dev/null

# Look for package/dependency manifests
find . -maxdepth 2 -type f \( -name "package.json" -o -name "requirements.txt" -o -name "Cargo.toml" -o -name "pom.xml" -o -name "build.gradle" -o -name "go.mod" -o -name "setup.py" -o -name "pyproject.toml" \) 2>/dev/null

# Check recent changes if Git is available
if command -v git >/dev/null 2>&1; then
  echo "=== Recent commits (git log --oneline -10) ==="
  git log --oneline -10
  echo "=== Checking for uncommitted changes ==="
  git status --short
else
  echo "Git not available; skipping recent change check."
fi
```

## 2. Identify Purpose and Documentation

Look for information about what the codebase does:

```bash
# Examine README/documentation
if [ -f README.md ]; then head -50 README.md; fi
if [ -f README.txt ]; then head -50 README.txt; fi
if [ -f doc/README.md ]; then head -50 doc/README.md; fi

# Look for doc/ or docs/ directory
ls -la doc/ 2>/dev/null || ls -la docs/ 2>/dev/null || echo "No doc/ or docs/ directory found"

# Check for website, homepage, or documentation links in package files
grep -i "homepage\|documentation\|repository" package.json 2>/dev/null || true
grep -i "homepage\|documentation\|url" setup.py 2>/dev/null || true
```

## Pitfalls

Don't assume structure.
