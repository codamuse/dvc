import argparse
import logging
from typing import TYPE_CHECKING

from funcy import compact, log_durations

from dvc.cli.command import CmdBase
from dvc.cli.utils import append_doc_link, fix_subparsers
from dvc.ui import ui

if TYPE_CHECKING:
    from dvc.repo.data import Status as DataStatus


logger = logging.getLogger(__name__)


class CmdDataStatus(CmdBase):
    COLORS = {
        "not_in_cache": "red",
        "committed": "green",
        "uncommitted": "yellow",
        "untracked": "cyan",
    }
    LABELS = {
        "not_in_cache": "Not in cache",
        "committed": "DVC committed changes",
        "uncommitted": "DVC uncommitted changes",
        "untracked": "Untracked files",
        "unchanged": "DVC unchanged files",
    }
    HINTS = {
        "not_in_cache": 'use "dvc pull <file>..." '
        "to update your local storage",
        "committed": "git commit the corresponding dvc files "
        "to update the repo",
        "uncommitted": 'use "dvc commit <file>..." to track changes',
        "untracked": 'use "git add <file> ..." or '
        'dvc add <file>..." to commit to git or to dvc',
        "git_dirty": "there are {}changes not tracked by dvc, "
        'use "git status" to see',
    }

    @staticmethod
    def _process_status(status: "DataStatus"):
        """Flatten stage status, and filter empty stage status contents."""
        for stage, stage_status in status.items():
            items = stage_status
            if isinstance(stage_status, dict):
                items = {
                    file: state
                    for state, files in stage_status.items()
                    for file in files
                }
            if not items:
                continue
            yield stage, items

    @classmethod
    def _show_status(cls, status: "DataStatus") -> int:
        git_info = status.pop("git")  # type: ignore[misc]
        result = dict(cls._process_status(status))
        if not result:
            no_changes = "No changes"
            if git_info.get("is_empty", False):
                no_changes += " in an empty git repo"
            ui.write(f"{no_changes}.")

        for idx, (stage, stage_status) in enumerate(result.items()):
            if idx:
                ui.write()

            label = cls.LABELS.get(stage, stage.capitalize() + " files")
            header = f"{label}:"
            color = cls.COLORS.get(stage, "normal")

            ui.write(header)
            if hint := cls.HINTS.get(stage):
                ui.write(f"  ({hint})")

            if isinstance(stage_status, dict):
                items = [
                    ": ".join([state, file])
                    for file, state in stage_status.items()
                ]
            else:
                items = stage_status

            for item in items:
                ui.write(f"\t[{color}]{item}[/]".expandtabs(8), styled=True)

        if (hint := cls.HINTS.get("git_dirty")) and git_info.get("is_dirty"):
            message = hint.format("other " if result else "")
            ui.write(f"[blue]({message})[/]", styled=True)
        return 0

    def run(self) -> int:
        with log_durations(logger.trace, "in data_status"):  # type: ignore
            status = self.repo.data_status(
                granular=self.args.granular,
                untracked_files=self.args.untracked_files,
                with_dirs=self.args.with_dirs,
            )

        if not self.args.unchanged:
            status.pop("unchanged")  # type: ignore[misc]
        if self.args.untracked_files == "no":
            status.pop("untracked")
        if self.args.json:
            status.pop("git")  # type: ignore[misc]
            ui.write_json(compact(status))
            return 0
        return self._show_status(status)


def add_parser(subparsers, parent_parser):
    data_parser = subparsers.add_parser(
        "data",
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    data_subparsers = data_parser.add_subparsers(
        dest="cmd",
        help="Use `dvc data CMD --help` to display command-specific help.",
    )
    fix_subparsers(data_subparsers)

    DATA_STATUS_HELP = (
        "Show changes between the last git commit, "
        "the dvcfiles and the workspace."
    )
    data_status_parser = data_subparsers.add_parser(
        "status",
        parents=[parent_parser],
        description=append_doc_link(DATA_STATUS_HELP, "data/status"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help=DATA_STATUS_HELP,
    )
    data_status_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Show output in JSON format.",
    )
    data_status_parser.add_argument(
        "--show-json",
        action="store_true",
        default=False,
        dest="json",
        help=argparse.SUPPRESS,
    )
    data_status_parser.add_argument(
        "--granular",
        action="store_true",
        default=False,
        help="Show granular file-level info for DVC-tracked directories.",
    )
    data_status_parser.add_argument(
        "--unchanged",
        action="store_true",
        default=False,
        help="Show unmodified DVC-tracked files.",
    )
    data_status_parser.add_argument(
        "--untracked-files",
        choices=["no", "all"],
        default="no",
        const="all",
        nargs="?",
        help="Show untracked files.",
    )
    data_status_parser.add_argument(
        "--with-dirs",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    data_status_parser.set_defaults(func=CmdDataStatus)
