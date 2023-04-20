import signal
import logging
import typing
from importlib import metadata, resources

from file_mover_for_google_drive.common import models

logger = logging.getLogger(__name__)


def get_name_dash() -> str:
    """Get the package name with word separated by dashes."""
    return "file-mover-for-google-drive"


def get_name_under() -> str:
    """Get the package name with word separated by underscores."""
    return "file_mover_for_google_drive"


def get_prog_description() -> str:
    """Get the program description."""
    return "Helps move files between Google Drive accounts."


def get_version() -> typing.Optional[str]:
    """Get the package version."""
    try:
        dist = metadata.distribution(get_name_dash())
        return dist.version
    except metadata.PackageNotFoundError:
        pass

    try:
        with resources.as_file(
            resources.files(get_name_under()).joinpath("cli.py")
        ) as file_path:
            version_path = file_path.parent.parent.parent / "VERSION"
            return version_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        pass

    return None


class GracefulExit:
    """
    Capture Ctrl + C (default KeyboardInterrupt) via SIGINT
    and allow graceful exit.
    """

    # https://stackoverflow.com/a/57649638/31567

    def __init__(self):
        self.state = False
        # when a SIGINT occurs, run the change_state method
        signal.signal(signal.SIGINT, self.change_state)

    def change_state(self, signum, frame):
        """When a SIGINT occurs, indicate that the program should exit."""
        print("")
        print("===============================================================")
        print("NOTICE: Detected request to exit. Program will gracefully exit.")
        print("        Repeat the request to exit to stop immediately. ")
        print(
            "WARNING: Stopping immediately might cause files, folders, or reports to end up in an inconsistent state."
        )
        print("===============================================================")
        print("")

        # change to perform the default function for the signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # set the flag to indicate the program should exit
        self.state = True

    def should_exit(self):
        return self.state


class GoogleDriveEntryCache:
    def __init__(self, top_folder_id: str):
        self._top_folder_id = top_folder_id
        self._cache: dict[str, models.GoogleDriveEntry] = {}

    def add(self, entry: models.GoogleDriveEntry) -> None:
        """Add an entry to the cache."""
        self._cache[entry.entry_id] = entry

    def get(self, entry_id: str) -> typing.Optional[models.GoogleDriveEntry]:
        """Get an entry from the cache."""
        result = self._cache.get(entry_id)
        if not result:
            return None
        return result

    def delete(self, entry_id: str) -> typing.Optional[models.GoogleDriveEntry]:
        """Remove an entry from the cache."""
        return self._cache.pop(entry_id, None)

    def path(self, entry_id: str) -> list[models.GoogleDriveEntry]:
        result = []
        current_id = entry_id
        while True:
            entry = self._cache.get(current_id)
            if not entry:
                raise ValueError(f"Could not get entry id '{current_id}'.")

            result.append(entry)

            if entry.entry_id == self._top_folder_id:
                break

            current_id = entry.parent_id

        result.reverse()
        return result
