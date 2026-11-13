---
name: benchmark-driven-development
description: "Use when implementing benchmark: read, explore, implement."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [benchmark, feature-implementation, testing, tdd]
    related_skills: [test-driven-development, systematic-debugging]
---

# Benchmark-Driven Development

## Overview

Implement a feature specified by a benchmark file (e.g., BENCHMARK.md).

**Core principle:** The benchmark is the source of truth. If the test does not match the benchmark, fix the test.

## When to Use

- When you have a benchmark file describing a required feature or behavior.
- When you need to implement a feature and verify it with tests.

## Procedure

### 1. Read the benchmark

Use `read_file` to read the benchmark file (e.g., BENCHMARK.md).

Understand:
- What feature or behavior is required.
- Any constraints or specific instructions.

### 2. Explore the repository

Use `ls`, `find`, or `search_files` to understand the repository structure.

Identify:
- Source code directories.
- Test directories.
- Relevant files that may need to be changed.

### 3. Examine existing code and tests

Read the relevant source code and test files.

Determine:
- If the feature is already implemented.
- If there is an existing test for the feature.
- If the existing test is broken or missing.

### 4. Identify the gap

Compare the benchmark requirement with the current implementation.

Ask:
- What is missing?
- What is incorrect?
- What needs to be changed?

### 5. Implement or fix

- If the feature is missing, implement it following TDD (write a failing test first, then minimal code to pass).
- If the feature is present but the test is broken, fix the test first to match the benchmark (making sure it fails if the feature is missing, then fix the implementation or the test to pass).
- If the feature and test are correct, no action is needed.

### 6. Verify

Run the tests to ensure they pass.

Run the full test suite to check for regressions.

### 7. Ensure confinement

Do not modify files outside the repository.

## Pitfalls

- **Do not assume the test is correct.** The benchmark is the source of truth. If the test does not match the benchmark, fix the test.
- **When fixing tests, ensure mocks are set up correctly.** For Vitest, use `vi.mock` at the top level and reset modules in `beforeEach`.
- **When testing modules that depend on external engine or SDK packages, mock those dependencies at the top level and reset modules before importing the module under test.**
- **Avoid horizontal slicing.** Implement one behavior at a time using vertical tracer bullets (write a failing test, implement to pass, then move to the next).

## User Preferences

- Prefer AI-assisted command-line exploration: use terminal commands to list files and examine content.
- Value clear, detailed technical explanations: when documenting changes, be explicit about what was changed and why.
- Trust the AI to perform preliminary scans: use `search_files` and `read_file` to gather information before making changes.

## Verification Checklist

Before marking work complete:

- [ ] Benchmark file has been read and understood.
- [ ] Repository structure explored.
- [ ] Relevant source code and test files examined.
- [ ] Gap between benchmark and current state identified.
- [ ] Feature implemented or test fixed as needed.
- [ ] Tests pass (specific test and full suite).
- [ ] No files outside the repository modified.
- [ ] Output pristine (no errors, warnings).

## Example: Fixing a Broken Test

If a test exists but is broken (e.g., incorrect mocks), follow these steps:

1. Reset modules before each test to ensure mocks are fresh.
2. Mock dependencies at the top level (outside the test function) using `vi.mock`.
3. Provide mock implementations that match the benchmark requirement.
4. Re-import the module under test after mocks are set up.
5. Verify the test fails when the feature is missing (if applicable) and passes when the feature is present.

This ensures the test is isolated and reliable.
