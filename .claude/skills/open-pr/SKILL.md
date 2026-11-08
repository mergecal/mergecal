---
name: open-pr
description: Use when opening a pull request in this repo. Fills .github/pull_request_template.md and opens the PR as a draft.
---

MergeCal is open source. Every PR is public.

1. Build the story from all the commits on the branch, not from memory, so
   this works from a fresh session.
2. Fill in `.github/pull_request_template.md` and pass it with `--body`.
   `gh pr create --body` does not apply the template on its own.
3. **Description:** tell a short story about why: the problem, who hit it,
   and why this fix. Don't list what changed; the diff shows that.
4. **Privacy:** never include real data. No user names, emails, calendar
   names, URLs or UUIDs, event contents, Sentry or log excerpts with user
   details, or business details. Say "users", never "customers". If an
   example is needed, make one up or anonymize it.
5. **AI disclosure:** end the body with this, using your tool and model.
   Leave "Reviewed by:" blank; only the human reviewer fills it in.

   ```markdown
   ## AI disclosure
   Written with Claude Code (claude-opus-5-5).

   Reviewed by:
   ```
6. Open it as a draft: `gh pr create --draft`.
