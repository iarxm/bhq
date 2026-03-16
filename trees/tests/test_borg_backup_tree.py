import unittest

from borg_backup_tree import ArchiveSnapshot, TreeNode, build_archive_tree, render_output


class BorgBackupTreeTests(unittest.TestCase):
    def test_build_and_render_archive_tree(self) -> None:
        snapshot = ArchiveSnapshot(
            name="daily-2026-03-15",
            start="2026-03-15T09:00:00",
            archive_id="1234567890abcdef",
            hostname="host1",
            username="alice",
            command_line=None,
        )
        build_archive_tree(
            snapshot,
            [
                {"path": "etc", "type": "d", "mtime": "2026-03-15T08:59:00"},
                {"path": "etc/hosts", "type": "f", "size": 128, "mtime": "2026-03-15T08:59:30"},
                {"path": "var/log", "type": "d", "mtime": "2026-03-15T08:00:00"},
            ],
        )

        rendered = render_output(
            repository="repo",
            snapshots=[snapshot],
            metadata_mode="compact",
            max_depth=None,
            show_command_line=False,
            archives_only=False,
        )

        self.assertIn("repo", rendered)
        self.assertIn("daily-2026-03-15 [2026-03-15 09:00:00 | host1 | alice]", rendered)
        self.assertIn("etc [dir | 2026-03-15 08:59:00]", rendered)
        self.assertIn("hosts [file | 128B | 2026-03-15 08:59:30]", rendered)

    def test_max_depth_stops_recursion(self) -> None:
        snapshot = ArchiveSnapshot(
            name="a1",
            start=None,
            archive_id=None,
            hostname=None,
            username=None,
            command_line=None,
            root=TreeNode(name=""),
        )
        build_archive_tree(
            snapshot,
            [
                {"path": "a/b/c.txt", "type": "f", "size": 1},
            ],
        )

        rendered = render_output(
            repository="repo",
            snapshots=[snapshot],
            metadata_mode="none",
            max_depth=1,
            show_command_line=False,
            archives_only=False,
        )

        self.assertIn("a", rendered)
        self.assertNotIn("c.txt", rendered)


if __name__ == "__main__":
    unittest.main()
