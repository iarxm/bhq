TASK make this more general than borg specific. A general tree structure plain text gen to be committed to vcs

# Borg Backup Tree

`borg_backup_tree.py` renders a `tree`-style metadata view for every archive in a Borg repository.

## What it does

- Lists archives with Borg's JSON repository listing.
- Traverses each archive with `borg list --json-lines`.
- Renders `repository -> archive -> filesystem tree`.
- Adds compact or full metadata next to archives and files.

## Usage

```bash
python3 borg_backup_tree.py /path/to/repo
python3 borg_backup_tree.py user@host:repo --last 10 --max-depth 2
python3 borg_backup_tree.py /path/to/repo --archives-only --metadata full
python3 borg_backup_tree.py /path/to/repo --glob-archives 'daily-*' --show-command-line
```

## Notes

- This reads every selected archive, so large repositories can take time.
- The program shells out to `borg`; use `--borg-bin` if it is not on `PATH`.
- Metadata modes:
  - `none`: names only
  - `compact`: type, size, and timestamp when available
  - `full`: compact data plus owner, group, mode, health, and archive id
