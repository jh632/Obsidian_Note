---
name: surgical-code-edit
description: Apply the user's concise code-editing rules when modifying existing code, fixing bugs, refactoring, or editing C/ESP-IDF modules: keep changes minimal, surgical, validated, style-compatible, and avoid unrelated cleanup or overengineering.
---

# Surgical Code Edit

Use these rules when changing code.

## Before Editing

- State key assumptions when the request is ambiguous.
- If multiple interpretations are plausible, list them and ask before editing when the wrong choice would cause rework.
- Prefer the simplest implementation that satisfies the request.

## Change Scope

- Modify only code directly required by the user's request.
- Do not refactor, reformat, rename, or clean up unrelated code.
- Follow the existing local style even when another style is also reasonable.
- Remove unused imports, variables, or helpers only when your own change created them.
- Do not delete pre-existing dead code unless the user asks.

## Implementation

- Do not add unrequested flexibility, configuration, abstractions, or future-facing APIs.
- Avoid one-off helper wrappers when direct code is clearer.
- Keep one authoritative description for shared behavior, usually in the public header or closest existing contract.
- Keep comments brief and useful; use Chinese comments when the module or user request expects Chinese.

## C And ESP-IDF Rules

- In C modules, `.c` files include only their matching `.h`.
- Put required external includes in the header when the project style requires it.
- Prefer handle/ops or object-like APIs when practical and consistent with nearby code.
- Keep logs lowercase and short.
- Error logs include `failed` and key-value fields such as `err=%s`, `timeout_ms=%lu`, `len=%u`, `expected=%u`, and `got=%u`.
- Log only key success events.

## Verification

- Define a concrete success check before or during the edit.
- For bug fixes, prefer a reproducing test or direct source-level proof.
- For refactors, verify behavior-equivalent call sites.
- Run the narrowest relevant check available, such as focused tests, build target, formatter, or `git diff --check`.
- If verification is blocked by the environment, report the blocker separately from source-code findings.
