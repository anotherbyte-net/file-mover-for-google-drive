import abc
import logging
import typing

from file_mover_for_google_drive.common import (
    models,
    client,
    interact,
    utils,
    report_plan,
    report,
)

logger = logging.getLogger(__name__)


class BaseManage(abc.ABC):
    _log_batch_size = 10

    def __init__(
        self,
        config: models.ConfigProgram,
        gd_client: typing.Optional[client.GoogleApiClient] = None,
    ) -> None:
        """
        Subclasses must call init to create an instance.

        Args:
            config: The configuration for this action.
            gd_client: The Google Drive client. Used for testing.
        """
        if not gd_client:
            gd_client = client.GoogleApiClient.get_drive_client(config)

        self._config = config
        self._client = gd_client
        self._api = interact.GoogleDriveApi(config, gd_client)
        self._container = interact.GoogleDriveContainer(
            google_drive_api=self._api,
            account=self._api.config.account,
        )
        self._actions = interact.GoogleDriveActions(self._container)
        self._cache = utils.GoogleDriveEntryCache(config.account.top_folder_id)
        self._plan_builder = report_plan.PlanReportBuilder(config.account)

        # allow cancelling without issues
        self._graceful_exit = utils.GracefulExit()

    def run(self) -> bool:
        """Run the action.

        Returns:
            The outcome of the action.
        """
        raise NotImplementedError()

    def _iteration_check(self, index: int) -> bool:
        """Check an iteration.

        Args:
            index: The iteration index.

        Returns:
            True to stop iterating.
        """
        if index > 0 and (index + 1) % self._log_batch_size == 0:
            logger.info("Processed %s entries.", index + 1)

        if self._graceful_exit.should_exit():
            logger.warning("Stopping early.")
            return True

        return False

    def _iterate_entries(self, process_one_func, **kwargs: report.ReportCsv) -> bool:
        """Process each entry.

        Args:
            process_one_func: The function to process one entry.
            **kwargs: The reports to build.

        Returns:
            True for success or False for failure or early exit.
        """
        config = self._config
        actions = self._actions

        account = config.account

        top_folder_id = account.top_folder_id

        entry_count = 0

        # top entry
        top_entry = actions.get_entry(top_folder_id)
        entry_count += 1
        process_one_func(entry=top_entry, **kwargs)

        logger.info("Starting folder is '%s'.", top_entry.name)

        # descendants
        for index, entry in enumerate(actions.get_descendants(top_folder_id)):
            entry_count += 1

            process_one_func(entry=entry, **kwargs)

            if self._iteration_check(index):
                break

        logger.info("Processed total of %s entries.", entry_count)
        logger.info("Finished.")

        return not self._graceful_exit.should_exit()
