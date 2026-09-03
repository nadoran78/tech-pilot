---
name: gh-create-develop-pr
description: Validate a committed Issue branch and, only after explicit user confirmation, push it and create a Draft GitHub pull request targeting develop. Use when the user asks Codex to prepare, open, publish, or create a feature, fix, docs, or chore PR for this repository. Do not use for release or hotfix PRs targeting main, for merging PRs, or for uncommitted implementation work.
---

# Create a Draft PR to Develop

Validate the complete branch diff before changing GitHub. Treat push and PR creation as explicit external writes.

## Read Project Context

1. Read the repository `AGENTS.md`.
2. Read `docs/INDEX.md`, the active phase document, and `docs/process/development-workflow.md`.
3. Read the linked Issue and only the additional documents needed to verify its scope.

## Preflight

1. Verify that the current directory is inside a Git repository.
2. Run `gh auth status` and stop with recovery guidance if authentication is unavailable.
3. Resolve `origin`; do not guess an owner, repository, or base branch.
4. Fetch `origin/develop` and `origin/main` without force or destructive cleanup.
5. Reject `main`, `develop`, detached HEAD, and branch names outside `feature/*`, `fix/*`, `docs/*`, or `chore/*`.
6. Require an Issue number in the branch name and confirm that the open Issue exists.
7. Require a clean working tree. Do not stage or commit files in this skill.
8. Check for an existing open PR from the same branch before creating another.
9. Compare the branch against `origin/develop` and report whether it is behind, conflicted, empty, or unexpectedly broad.

Stop if the branch has no commits for `develop`, contains unresolved conflicts, or cannot be related confidently to the linked Issue.

## Verify the Change

1. Review every changed file and commit against the Issue Scope and Acceptance Criteria.
2. Identify unrelated files, accidental generated output, secrets, credentials, local paths, and unsafe configuration.
3. Run the verification commands documented by the repository for the changed area.
4. Perform a focused self-review of the complete `origin/develop...HEAD` diff. Incorporate an existing Codex `/review` result when available.
5. Record passed, failed, unavailable, and intentionally skipped checks separately.

Stop before publication when a required check fails or a possible secret is present. Allow an exception only after the user explicitly accepts the disclosed risk; never override secret exposure.

## Draft the PR

Use the repository PR template when available. Include:

- an outcome-oriented title;
- `Closes #<issue>`;
- base `develop` and the exact head branch;
- why the chosen approach fits the Issue;
- the main changes;
- executed and missing verification;
- risks and follow-up work;
- changed files in the recommended review order.

Default to a Draft PR. Do not mark it Ready or merge it.

## Apply the Publication Gate

Default to prepare mode. Show the repository, base, head, title, complete body, commit summary, diff summary, and verification results without pushing or creating a PR.

Publish only when the user explicitly asks to push and create the exact Draft PR. If the branch, diff, title, body, or verification changes materially after approval, show the revised preview and request confirmation again.

Push only the current short-lived branch with a normal upstream push. Then create the PR with base `develop`, the exact head branch, and Draft status. Never use force push.

## Report the Result

After publication, return:

- PR number and clickable URL;
- linked Issue;
- base and head branches;
- validation summary and any missing checks;
- recommended file review order;
- explicit reminder that Ready transition and merge remain user actions.

If creation fails after push, report that the branch was pushed but the PR may not exist. Check for an existing PR before retrying.

## Safety Boundaries

- Never target `main`; release and hotfix flows require separate procedures.
- Never push `main` or `develop`, force push, merge, close the Issue manually, or alter branch protection.
- Never stage, commit, amend, rebase, reset, stash, or discard user changes.
- Never publish a PR with an ambiguous Issue, base, repository, or diff.
- Never hide failed, skipped, or unavailable validation.
