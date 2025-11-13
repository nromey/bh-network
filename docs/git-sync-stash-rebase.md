# Git: Stash, Rebase, Resolve — a practical guide

This is a hands‑on recipe for syncing your local `main` with `origin/main` when you have uncommitted work, and for resolving conflicts cleanly — especially for generated files like `_data/next_net.yml`.

Use this when a push is rejected with “remote contains work that you do not have locally” or when you want a clean, linear history without merge bubbles.

## TL;DR (copy/paste)

1) Park your local changes (including untracked):
- `git stash push -u -m "wip: <topic>"`

2) Sync your branch with the latest remote:
- `git fetch origin`
- `git rebase origin/main`

3) If you hit conflicts in generated files (e.g., `_data/next_net.json`), regenerate then continue:
- `python3 scripts/build_next_net.py`
- `git add _data/next_net.yml`
- `git rebase --continue`

4) Push:
- `git push`

5) Restore your stashed work:
- `git stash pop`  (or `git stash apply` if you want to keep the stash)

## Why rebase and stash?

- Rebase keeps history linear by replaying your local commits on top of the remote branch. That makes the log easy to read and avoids merge bubbles for routine syncs.
- Stash temporarily shelves uncommitted changes so rebase can proceed on a clean tree. It’s safer than committing half‑baked work to `main`.

## Full flow with explanations

1) Check where you are
- `git status -sb`
- `git log --oneline --graph --decorate -n 10`

2) Stash in‑progress work (tracked + untracked)
- `git stash push -u -m "wip: <topic>"`
- Inspect stashes: `git stash list`

3) Update and rebase
- `git fetch origin`
- `git rebase origin/main`

4) Resolve conflicts
- For regular source files: open the file(s), fix the conflict markers, then `git add <files>` and `git rebase --continue`.
- For generated artifacts (this repo):
  - `_data/next_net.json` is produced by `scripts/build_next_net.py`. Prefer “regenerate” over manual merging:
    - `python3 scripts/build_next_net.py`
    - `git add _data/next_net.yml`
    - `git rebase --continue`

5) Push
- `git push`

6) Restore your work
- `git stash pop` (apply and drop)
- If you prefer to keep the stash until you verify everything: `git stash apply stash@{0}` then `git stash drop stash@{0}` later.

## Useful variants

- Abort rebase: `git rebase --abort`
- Skip a problematic commit: `git rebase --skip`
- Resolve by choosing one side quickly (then regenerate):
  - “ours” (your side of the rebase): `git checkout --ours _data/next_net.yml`
  - “theirs” (incoming): `git checkout --theirs _data/next_net.yml`
  - Then run the generator and `git add`, `git rebase --continue`.
- Stash to a branch: `git stash branch wip/<topic> stash@{0}` (great for longer detours)

## Rebase vs merge (when to choose which)

- Rebase (`git fetch && git rebase origin/main`) keeps history linear and is ideal for local syncs.
- Merge (`git pull --no-rebase`) is fine for integrating feature branches that were shared by others, or when you want to preserve the “merge” event itself.

## Repo‑specific notes

- Generated files:
  - `_data/next_net.json` comes from `scripts/build_next_net.py`.
  - `_data/bhn_ncos_schedule.yml` comes from `scripts/build_bhn_data.py`.
  - When they conflict, regenerate instead of hand‑editing.
- CI commits:
  - The GitHub Actions workflow commits schedule/next_net only when content truly changes; a push can land while you’re working locally — rebase handles this cleanly.

## On secrets, API keys, and that comment

Context: There was feedback about a script that interacted with a GPG‑protected API key and a suggestion to “use GitHub Secrets.” Here’s the practical view:

- GitHub Secrets are for CI/CD (Actions) and are not accessible from your local shell. If you run a local helper like `~/oai_loginmethod`, GitHub Secrets aren’t directly applicable. Use local secure storage: environment variables, a password manager/keychain, or GPG‑encrypted files kept outside the repo.
- Never commit plain‑text secrets. Even if a file is later deleted, history keeps it. Public repos are scraped; revoking / rotating leaked keys is the only safe remedy.
- GPG‑encrypted blobs: Storing an encrypted file in a repo can be acceptable if the passphrase isn’t in the repo and operational risk is understood. However:
  - Ensure the decrypt workflow is documented for authorized users and doesn’t leak the passphrase (avoid echoing, command history, etc.).
  - Consider .gitignore for any decrypted outputs.
  - For CI use cases, prefer GitHub Secrets over committing encrypted files.

Bottom line: Your approach of keeping the sensitive material outside the repo and unlocking locally is reasonable for local workflows. For automation, route secrets via GitHub Secrets (Actions) or other CI secret stores — not in the repository.

## Etiquette (process comments)

- If something looks risky or confusing, the right venue is a GitHub Issue in this repo. That creates a transparent record, assigns ownership, and avoids back‑channel confusion.
- PRs with suggested improvements are even better. Emailing third parties without opening an issue makes it hard to track and resolve.

---

Questions or improvements? Open an Issue with the exact command you ran and the error you saw; include `git status -sb` output. We can refine this doc as needed.
