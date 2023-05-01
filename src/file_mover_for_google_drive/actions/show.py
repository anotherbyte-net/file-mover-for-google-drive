"""The show action."""

import logging

from file_mover_for_google_drive.common import manage, report, models

logger = logging.getLogger(__name__)


class Show(manage.BaseManage):
    """
    Show all the folder, files, and permissions in a Google Drive,
    starting at a given personal or business account folder.
    """

    def run(self) -> bool:
        """Run the 'show' action."""

        config = self._config
        account = config.account
        reports = config.reports

        entries_dir = reports.entries_dir
        permissions_dir = reports.permissions_dir

        logger.info(
            "Show entries for %s account '%s'.",
            account.account_type.name,
            account.account_id,
        )

        # reports
        rpt_entries = report.ReportCsv(entries_dir, report.EntryReport)
        rpt_permissions = report.ReportCsv(permissions_dir, report.PermissionReport)

        # build
        with rpt_entries, rpt_permissions:
            logger.info("Writing entries report '%s'.", rpt_entries.path.name)
            logger.info("Writing permissions report '%s'.", rpt_permissions.path.name)

            result = self._iterate_entries(
                self._process_one,
                rpt_entries=rpt_entries,
                rpt_permissions=rpt_permissions,
            )
            return result

    def _process_one(
        self,
        entry: models.GoogleDriveEntry,
        rpt_entries: report.ReportCsv,
        rpt_permissions: report.ReportCsv,
    ) -> None:
        """Process one entry."""

        cache = self._cache
        cache.add(entry)

        entry_path = cache.path(entry.entry_id)
        logger.info("Processing %s.", str(entry))

        for row in report.EntryReport.from_entry_path(entry_path):
            rpt_entries.write_item(row)

        for row in report.PermissionReport.from_entry_path(entry_path):
            rpt_permissions.write_item(row)
