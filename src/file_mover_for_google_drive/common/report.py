import abc
import csv
import dataclasses
import logging
import pathlib
import typing
from datetime import datetime

from file_mover_for_google_drive.common import models

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BaseReport:
    @classmethod
    def report_name(cls):
        raise NotImplementedError()

    @classmethod
    def fields(cls):
        raise NotImplementedError()


class ReportCsv:
    def __init__(self, top_dir: pathlib.Path, report: type[BaseReport]):
        self._top_dir = top_dir
        self._report = report

        self._file_date = datetime.now()
        self._writer: typing.Optional[csv.DictWriter] = None
        self._file_path: typing.Optional[pathlib.Path] = None
        self._file_handle: typing.Optional[typing.TextIO] = None

    @property
    def path(self):
        return self._file_path

    def start(self):
        """Start the report file."""

        name = self._report.report_name()
        fields = self._report.fields()

        file_date_str = self._file_date.isoformat(sep="-", timespec="seconds")
        file_date_str = file_date_str.replace(":", "-")

        file_name = f"{file_date_str}-{name}"
        report_file = (self._top_dir / file_name).with_suffix(".csv")
        report_file.parent.mkdir(exist_ok=True, parents=True)

        self._file_path = report_file
        self._file_handle = open(report_file, "wt", newline="")
        self._writer = csv.DictWriter(self._file_handle, fields)
        self._writer.writeheader()

    def write_item(self, item: dict):
        """Write an item for the report."""
        if self._writer:
            self._writer.writerow(item)
        else:
            raise ValueError("Csv writer is not ready.")

    def read(self, name: str) -> typing.Iterable[BaseReport]:
        # TODO: read file in self._top_dir with name using self._report.
        raise NotImplementedError()

    def finish(self):
        """Finish the report and close the file."""

        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

        if self._writer:
            self._writer = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        return False


@dataclasses.dataclass
class BaseEntryReport(abc.ABC):
    entry_name: str
    """name of the file or folder"""
    entry_path: str
    """path from top of collection to the entry"""
    entry_type: str
    """either 'file' or 'folder' ('permission' is not a possible value)"""
    collection_type: str
    """either 'business' or 'personal'"""
    collection_name: str
    """
    either the shared drive name for a business account or 
    'My Drive' for a personal drive
    """
    collection_id: str
    """either the shared drive domain or the email for the current user"""
    link: str
    """Google Drive link to the file or folder the permission is applied to"""
    entry_id: str
    """file or folder id"""


@dataclasses.dataclass
class EntryReport(BaseReport, BaseEntryReport):
    checksum: str
    """content uniqueness value for 'binary' / non-Google files"""
    quota_bytes: typing.Optional[int]
    """Google Drive quota used by the file or folder (may include multiple versions)"""
    size_bytes: int
    """actual size of the current version of the file or folder"""

    @classmethod
    def report_name(cls):
        return "entries"

    @classmethod
    def fields(cls):
        return [f.name for f in dataclasses.fields(cls)]

    @classmethod
    def from_entry_path(cls, entry_path: list[models.GoogleDriveEntry]):
        entry = entry_path[-1]
        parent_path_str = entry.build_path_str(entry_path[:-1])
        yield {
            "entry_name": entry.name,
            "entry_path": parent_path_str,
            "entry_type": entry.entry_type,
            "collection_type": entry.collection_type,
            "collection_name": entry.collection_name,
            "collection_id": entry.collection_id,
            "link": entry.view_link,
            "checksum": entry.checksum_sha256,
            "quota_bytes": entry.quota_bytes,
            "size_bytes": entry.size_bytes,
            "entry_id": entry.entry_id,
        }


@dataclasses.dataclass
class PermissionReport(BaseReport, BaseEntryReport):
    user_name: str
    """user's name"""
    user_email: str
    """user email"""
    user_access: str
    """the role"""

    permission_id: str
    """permission id (used for permissions, empty for files and folders)"""

    @classmethod
    def report_name(cls):
        return "permissions"

    @classmethod
    def fields(cls):
        return [f.name for f in dataclasses.fields(cls)]

    @classmethod
    def from_entry_path(cls, entry_path: list[models.GoogleDriveEntry]):
        entry = entry_path[-1]
        parent_path_str = entry.build_path_str(entry_path[:-1])

        for perm in entry.permissions:
            yield {
                "user_name": perm.user_name,
                "user_email": perm.user_email,
                "user_access": perm.role,
                "entry_name": entry.name,
                "entry_path": parent_path_str,
                "entry_type": entry.entry_type,
                "collection_type": entry.collection_type,
                "collection_name": entry.collection_name,
                "collection_id": entry.collection_id,
                "link": entry.view_link,
                "entry_id": entry.entry_id,
                "permission_id": perm.entry_id,
            }


@dataclasses.dataclass
class PlanReport(BaseReport):
    item_action: str
    """'create', 'update', 'delete', 'copy', 'transfer' (don't record 'retrieve')"""
    item_type: str
    """either 'file' or 'folder' or 'permission' (a permission is not an 'entry')"""
    entry_id: typing.Optional[str]
    """file or folder id"""
    permission_id: typing.Optional[str]
    """permission id (used for permissions, empty for files and folders)"""
    description: str
    """for the plan: free-text details of the planned change;
     for the outcome: details of success, failure, skipping"""

    begin_user_name: typing.Optional[str]
    """user's name"""
    begin_user_email: typing.Optional[str]
    """user email"""
    begin_user_access: typing.Optional[str]
    """the role"""
    begin_entry_name: typing.Optional[str]
    """name of the file or folder"""
    begin_entry_path: typing.Optional[str]
    """path from top of collection to the entry"""
    begin_collection_type: typing.Optional[str]
    """either 'business' or 'personal'"""
    begin_collection_name: typing.Optional[str]
    """
    either the shared drive name for a business account or 
    'My Drive' for a personal drive
    """
    begin_collection_id: typing.Optional[str]
    """either the shared drive domain or the email for the current user"""

    end_user_name: typing.Optional[str]
    """user's name"""
    end_user_email: typing.Optional[str]
    """user email"""
    end_user_access: typing.Optional[str]
    """the role"""
    end_entry_name: typing.Optional[str]
    """name of the file or folder"""
    end_entry_path: typing.Optional[str]
    """path from top of collection to the entry"""
    end_collection_type: typing.Optional[str]
    """either 'business' or 'personal'"""
    end_collection_name: typing.Optional[str]
    """
    either the shared drive name for a business account or 
    'My Drive' for a personal drive
    """
    end_collection_id: typing.Optional[str]
    """either the shared drive domain or the email for the current user"""

    @classmethod
    def report_name(cls):
        return "plans"

    @classmethod
    def fields(cls):
        return [f.name for f in dataclasses.fields(cls)]

    @classmethod
    def from_path(cls, path: pathlib.Path):
        with open(path, "rt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield PlanReport(**row)

    def __str__(self):
        descr = self.description
        entry_name = self.end_entry_name or self.begin_entry_name
        entry_path = self.end_entry_path or self.begin_entry_path
        items = [
            f'"{descr}"',
            f"for entry '{entry_name}'" if entry_name else None,
            f"path '{entry_path}'" if entry_path else None,
        ]
        return " ".join([i for i in items if i])


@dataclasses.dataclass
class OutcomeReport(PlanReport):
    result_name: str
    """'succeeded' or 'failed' or 'skipped' (past tense, the plan has been executed to produce the outcome)"""

    @classmethod
    def report_name(cls):
        return "outcomes"

    @classmethod
    def fields(cls):
        result_names = ["result_name"]
        field_names = [
            f.name for f in dataclasses.fields(cls) if f.name not in result_names
        ]
        return result_names + field_names
