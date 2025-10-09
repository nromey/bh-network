Backups
=======

This folder can hold tarballs of the remote `/opt/bhn` JSON processor as an emergency backup.

How to create a backup locally
- Ensure you have SSH access to the remote host (and sudo rights to read `/opt/bhn`).
- Run:
  
  ```bash
  scripts/pull_opt_bhn.sh ner@andrel
  ```

- This writes `backups/bhn_opt_YYYYMMDD_HHMMSS.tar.gz`.

Notes
- The helper excludes obvious secrets (`*.env`, files containing `secret`/`token`, VCS folders, node_modules, __pycache__). Adjust as needed in `scripts/pull_opt_bhn.sh` before running.
- Inspect the archive before committing it:
  
  ```bash
  tar -tzf backups/bhn_opt_*.tar.gz | head
  ```

- Do not store credentials or private keys in this repo. If such files exist under `/opt/bhn`, add more excludes before pulling.
- Git LFS is enabled for `backups/*.tar.gz`, `backups/*.tar.xz`, and `backups/*.tar.bz2`.
  - On your machine, run `git lfs install` once before adding archives.
