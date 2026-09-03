---
name: gh-create-issue
description: Draft and, only after explicit user confirmation, publish one scoped GitHub Issue with GitHub CLI. Use when the user asks Codex to prepare, file, publish, or create a repository Issue from a task, plan, bug, feature, documentation change, or technical decision. Do not use for local-only task lists, pull requests, or automatic issue creation inferred from implementation work.
---

# Create a GitHub Issue

Prepare a reviewable Issue before changing GitHub. Treat publication as a separate, explicit external write.

## Read Project Context

1. Read the repository `AGENTS.md`.
2. Read `docs/INDEX.md`, the active phase document, and `docs/process/development-workflow.md` when present.
3. Read only the additional product or technical documents needed to scope the Issue.

## Preflight

1. Verify that the current directory is inside a Git repository.
2. Run `gh auth status` and stop with recovery guidance if authentication is unavailable.
3. Resolve the GitHub repository from `origin`; do not guess an owner or repository.
4. Search open Issues for the main outcome and likely synonyms.
5. If a likely duplicate exists, show it and ask whether to update, link, or create a distinct Issue. Do not publish a duplicate silently.

## Draft the Issue

Use the repository Issue template when available. Include:

- a concise outcome-oriented title;
- `Goal` describing the completed state;
- `Context` explaining why the work is needed and linking relevant documents;
- `Scope` as concrete, reviewable work items;
- `Acceptance Criteria` as observable results;
- `Non-Goals` preventing scope expansion;
- `Verification Plan` describing how completion will be checked.

Keep one Issue focused on one outcome. Separate unrelated work instead of expanding the Issue.

## Apply the Publication Gate

Default to prepare mode. Show the repository, title, complete body, and any duplicate candidates without creating anything.

Publish only when the user explicitly asks to create or publish the exact draft. If the draft changes materially after approval, show the revised draft and request confirmation again.

Use `gh issue create` with an exact title and body. Do not assign labels, milestones, projects, or people unless the user requested them or repository policy requires them.

## Report the Result

After publication, return:

- Issue number and clickable URL;
- final title;
- short scope summary;
- suggested branch type and slug, without creating the branch.

If publication fails, report the command failure and whether GitHub state may have changed. Do not retry a create command until checking whether the Issue was created.

## Safety Boundaries

- Never publish based only on implicit skill activation or an inferred future task.
- Never close, delete, transfer, or edit an existing Issue unless explicitly requested.
- Never include secrets, credentials, private local paths, or unrelated personal data.
- Never claim a duplicate search was complete if GitHub access or search failed.
- Never start implementation, create a branch, or open a PR as part of this skill.
