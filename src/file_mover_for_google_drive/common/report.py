"""The report classes."""
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
class BaseReport(abc.ABC):
    """The abstract base report data class."""

    @classmethod
    @abc.abstractmethod
    def report_name(cls) -> str:
        """Get the report name.

        Returns:
            The report name.
        """
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def fields(cls) -> list[str]:
        """Get the list of report fields.

        Returns:
            The field list.
        """
        raise NotImplementedError()


TypeReport_co = typing.TypeVar("TypeReport_co", bound="BaseReport", covariant=True)


class ReportCsv:
    """A CSV file report."""

    def __init__(self, top_dir: pathlib.Path, report: type[TypeReport_co]):
        """Create a new csv Report instance.

        Args:
            top_dir: The directory for the csv files.
            report: The type of report to create.
        """
        self._top_dir = top_dir
        self._report = report

        self._file_date = datetime.now()
        self._writer: typing.Optional[csv.DictWriter] = None
        self._file_path: typing.Optional[pathlib.Path] = None
        self._file_handle: typing.Optional[typing.TextIO] = None

    @property
    def path(self):
        """Get the file path.

        Returns:
            The file path.
        """
        return self._file_path

    def start(self) -> None:
        """Start the report file.

        This sets up the resources to write to the report file.

        Returns:
            None
        """

        name = self._report.report_name()
        fields = self._report.fields()

        file_date_str = self._file_date.isoformat(sep="-", timespec="seconds")
        file_date_str = file_date_str.replace(":", "-")

        file_name = f"{file_date_str}-{name}"
        report_file = (self._top_dir / file_name).with_suffix(".csv")
        report_file.parent.mkdir(exist_ok=True, parents=True)

        self._file_path = report_file
        self._file_handle = open(
            report_file,
            "wt",
            newline="",
            encoding="utf-8",
        )  # noqa: R1732
        self._writer = csv.DictWriter(self._file_handle, fields)
        self._writer.writeheader()

    def write_item(self, item: dict) -> None:
        """Write an item to the report file.

        Args:
            item: The item to write.

        Returns:
            None
        """
        if self._writer:
            self._writer.writerow(item)
        else:
            raise ValueError("Csv writer is not ready.")

    def read(self, name: str) -> typing.Iterable[TypeReport_co]:
        """Read the report file.

        Args:
            name: The name of the report file to read.

        Returns:
            The contents of the report file.
        """
        report_file = (self._top_dir / name).with_suffix(".csv")
        if not report_file.exists():
            raise ValueError(f"Plan file does not exist '{report_file}'.")
        with open(report_file, "rt", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                yield self._report(**row)

    def finish(self) -> None:
        """Finish the report and close the file.

        This ensures the resources to write the file are closed.

        Returns:
            None
        """

        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

        if self._writer:
            self._writer = None

    def __enter__(self) -> "ReportCsv":
        """Enter the runtime context

        Returns:
            The ReportCSV instance.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the runtime context.

        Args:
            exc_type: The exception type.
            exc_val: The exception value.
            exc_tb: The exception traceback.

        Returns:
            True to suppress any exception.
        """
        self.finish()


@dataclasses.dataclass
class BaseEntryReport(abc.ABC):
    """The abstract base for entry reports."""

    entry_name: str
    """name of the file or folder"""
    entry_path: str
    """path from top of the drive to the entry"""
    entry_type: str
    """either 'file' or 'folder' ('permission' is not a possible value)"""
    account_type: str
    """The type of account.
    One of 'personal', 'business'."""
    drive_id: str
    """The drive id.
    'My Drive' for personal accounts.
    The Shared Drive id for business accounts."""
    account_id: str
    """The account identifier.
    The email address for personal accounts.
    The domain name for business accounts."""
    link: str
    """Google Drive link to the file or folder the permission is applied to"""
    entry_id: str
    """file or folder id"""


@dataclasses.dataclass
class EntryReport(BaseReport, BaseEntryReport):
    """An item in an entry report."""

    checksum: str
    """content uniqueness value for 'binary' / non-Google files"""
    quota_bytes: typing.Optional[int]
    """Google Drive quota used by the file or folder (may include multiple versions)"""
    size_bytes: int
    """actual size of the current version of the file or folder"""

    @classmethod
    def report_name(cls):
        """Get the report name.

        Returns:
            The report name.
        """
        return "entries"

    @classmethod
    def fields(cls) -> list[str]:
        """Get the list of report fields.

        Returns:
            The field list.
        """
        return [f.name for f in dataclasses.fields(cls)]

    @classmethod
    def from_entry_path(cls, entry_path: list[models.GoogleDriveEntry]):
        """Create an entry report item from an entry path list."""
        entry = entry_path[-1]
        parent_path_str = entry.build_path_str(entry_path[:-1])
        yield {
            "entry_name": entry.name,
            "entry_path": parent_path_str,
            "entry_type": entry.entry_type,
            "account_type": entry.account.account_type.name,
            "drive_id": entry.account.drive_id,
            "account_id": entry.account.account_id,
            "link": entry.view_link,
            "checksum": entry.checksum_sha256,
            "quota_bytes": entry.quota_bytes,
            "size_bytes": entry.size_bytes,
            "entry_id": entry.entry_id,
        }


@dataclasses.dataclass
class PermissionReport(BaseReport, BaseEntryReport):
    """An item in a permission report."""

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
        """Get the report name.

        Returns:
            The report name.
        """
        return "permissions"

    @classmethod
    def fields(cls) -> list[str]:
        """Get the list of report fields.

        Returns:
            The field list.
        """
        return [f.name for f in dataclasses.fields(cls)]

    @classmethod
    def from_entry_path(
        cls, entry_path: list[models.GoogleDriveEntry]
    ) -> typing.Iterable[typing.Mapping]:
        """Create a permission report item from an entry path list.

        Args:
            entry_path: The list of entries.

        Returns:
            An iterable of dictionaries.
        """
        entry = entry_path[-1]
        parent_path_str = entry.build_path_str(entry_path[:-1])

        for perm in entry.permissions_all:
            yield {
                "user_name": perm.display_name,
                "user_email": perm.user_email,
                "user_access": perm.role.name,
                "entry_name": entry.name,
                "entry_path": parent_path_str,
                "entry_type": entry.entry_type,
                "account_type": entry.account.account_type.name,
                "drive_id": entry.account.drive_id,
                "account_id": entry.account.account_id,
                "link": entry.view_link,
                "entry_id": entry.entry_id,
                "permission_id": perm.entry_id,
            }


@dataclasses.dataclass
class PlanReport(BaseReport):
    item_action: str
    """The short name of the planned action."""
    item_type: str
    """either 'file' or 'folder' or 'permission' (a permission is not an 'entry')"""
    entry_id: typing.Optional[str]
    """file or folder id"""
    permission_id: typing.Optional[str]
    """permission id (used for permissions, empty for files and folders)"""
    description: str
    """for the plan: free-text details of the planned change;
     for the outcome: details of success, failure, skipping"""

    account_type: str
    """The type of account.
    One of 'personal', 'business'."""
    drive_id: str
    """The drive id.
    'My Drive' for personal accounts.
    The Shared Drive id for business accounts."""
    account_id: str
    """The account identifier.
    The email address for personal accounts.
    The domain name for business accounts."""

    begin_user_name: typing.Optional[str]
    """user's name"""
    begin_user_email: typing.Optional[str]
    """user email"""
    begin_user_access: typing.Optional[str]
    """the role"""
    begin_entry_name: typing.Optional[str]
    """name of the file or folder"""
    begin_entry_path: typing.Optional[str]
    """path from top folder to the entry"""

    end_user_name: typing.Optional[str]
    """user's name"""
    end_user_email: typing.Optional[str]
    """user email"""
    end_user_access: typing.Optional[str]
    """the role"""
    end_entry_name: typing.Optional[str]
    """name of the file or folder"""
    end_entry_path: typing.Optional[str]
    """path from top folder to the entry"""

    @classmethod
    def report_name(cls):
        """Get the report name.

        Returns:
            The report name.
        """
        return "plans"

    @classmethod
    def fields(cls) -> list[str]:
        """Get the list of report fields.

        Returns:
            The field list.
        """
        return [f.name for f in dataclasses.fields(cls)]

    def __str__(self):
        entry_name = self.begin_entry_name or self.end_entry_name
        entry_path = self.begin_entry_path or self.end_entry_path
        user_name = self.begin_user_name or self.end_user_name
        user_email = self.begin_user_email or self.end_user_email
        user_access = self.begin_user_access or self.end_user_access
        items = [
            self.item_action,
            f"{self.item_type} '{entry_name}'" if entry_name else None,
            f"path '{entry_path}'" if entry_path else None,
            f"user '{user_name}'" if user_name else None,
            f"email '{user_email}'" if user_email else None,
            f"access '{user_access}'" if user_access else None,
        ]
        return " ".join([i for i in items if i])


@dataclasses.dataclass
class OutcomeReport(PlanReport):
    result_name: models.PlanReportOutcomes
    """Either 'succeeded' or 'failed' or 'skipped' (past tense, the plan has been
    executed to produce the outcome)"""
    result_description: str
    """A longer description of the outcome of applying the plan."""

    @classmethod
    def report_name(cls):
        """Get the report name.

        Returns:
            The report name.
        """
        return "outcomes"

    @classmethod
    def fields(cls) -> list[str]:
        """Get the list of report fields.

        Returns:
            The field list.
        """
        result_names = ["result_name", "result_description"]
        field_names = [
            f.name for f in dataclasses.fields(cls) if f.name not in result_names
        ]
        return result_names + field_names
