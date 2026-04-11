# Contributing to RouteMinds

Thanks for contributing to RouteMinds.

## Workflow

1. Create a branch from `main` for your work.
2. Keep your change focused and small when possible.
3. Open a pull request against `main`.
4. Wait for at least one approval before merging.

## Branching

- Do not push directly to `main`.
- Use clear branch names that describe the change, for example `fix/map-marker-bug` or `feat/auth-ui`.

## Pull Requests

- Describe the problem being solved.
- Summarize the approach you took.
- Include screenshots for UI changes.
- Mention any follow-up work or known limitations.

## Before Opening a PR

Make sure your change is ready for review:

- frontend changes: run the relevant app locally and verify the user flow
- backend changes: run the relevant tests for the affected area
- keep unrelated refactors out of the same PR

## Review Expectations

- At least one approval is required before merge.
- Resolve review conversations before merge.
- New commits pushed to a PR may dismiss prior approvals.

## Merge Policy

- Pull requests are merged into `main` using squash merge.
- Merged branches are deleted after merge.

## Security

- Do not commit secrets, API keys, tokens, or local `.env` files.
- If you find a sensitive issue, contact the project owner privately instead of opening a public issue with exploit details.

## Questions

If you are unsure about the scope of a change, open a draft PR early so feedback can happen before too much work is done.
