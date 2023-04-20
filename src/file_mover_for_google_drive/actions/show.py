"""The show action."""

import logging


from file_mover_for_google_drive.common import (
    manage,
    interact,
    utils,
    report,
    models,
    client,
)

logger = logging.getLogger(__name__)


class Show(manage.BaseManage):
    """
    Show all the folder, files, and permissions in a Google Drive,
    starting at a given personal or business account folder.
    """

    def __init__(
        self,
        account: str,
        config: models.Config,
        gd_client: client.GoogleDriveAnyClientType = None,
    ) -> None:
        """Create a new Show instance."""

        super().__init__(config, gd_client)
        self._show_personal = account == "personal"
        self._show_business = account == "business"
        if not self._show_personal and not self._show_business:
            raise ValueError(
                "The value for 'account' must be 'personal' or 'business'."
            )

    def run(self) -> bool:
        """Run the 'show' action."""

        config = self._config

        if self._show_personal:
            container = self._personal_container
            top_folder_id = config.personal_account_top_folder_id
        elif self._show_business:
            container = self._business_container
            top_folder_id = config.business_account_top_folder_id
        else:
            raise ValueError(
                "The value for 'account' must be 'personal' or 'business'."
            )

        actions = interact.GoogleDriveActions(container)

        container_cache = utils.GoogleDriveEntryCache(top_folder_id)

        col_type = container.collection_type
        col_name = container.collection_name
        col_id = container.collection_id

        entries_dir = config.report_entries_dir
        perms_dir = config.report_permissions_dir

        logger.info("Show entries for '%s' in %s '%s'.", col_name, col_type, col_id)
        logger.info("Starting with folder '%s'.", top_folder_id)

        # reports
        rpt_entries = report.ReportCsv(entries_dir, report.EntryReport)
        rpt_permissions = report.ReportCsv(perms_dir, report.PermissionReport)

        # build
        with rpt_entries, rpt_permissions:
            logger.info("Writing entries report '%s'.", rpt_entries.path.name)
            logger.info("Writing permissions report '%s'.", rpt_permissions.path.name)

            logger.info("Starting.")

            entry_count = 0

            # top entry
            top_entry = actions.get_entry(top_folder_id)
            entry_count += 1
            self._process_one(container_cache, rpt_entries, rpt_permissions, top_entry)

            logger.info("Starting folder is '%s'.", top_entry.name)

            # descendants
            for index, entry in enumerate(actions.get_descendants(top_folder_id)):
                entry_count += 1

                self._process_one(container_cache, rpt_entries, rpt_permissions, entry)

                if self._iteration_check(index):
                    break

            logger.info("Processed total of %s entries.", entry_count)

        logger.info("Finished.")

        return not self._graceful_exit.should_exit()

    def _process_one(
        self,
        container_cache: utils.GoogleDriveEntryCache,
        rpt_entries: report.ReportCsv,
        rpt_permissions: report.ReportCsv,
        entry: models.GoogleDriveEntry,
    ) -> None:
        """Process one entry."""

        container_cache.add(entry)

        entry_path = container_cache.path(entry.entry_id)

        for row in report.EntryReport.from_entry_path(entry_path):
            rpt_entries.write_item(row)

        for row in report.PermissionReport.from_entry_path(entry_path):
            rpt_permissions.write_item(row)
