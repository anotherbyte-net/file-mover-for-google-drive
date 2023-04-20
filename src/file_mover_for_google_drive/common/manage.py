import logging

from file_mover_for_google_drive.common import models, client, interact, utils

logger = logging.getLogger(__name__)


class BaseManage:
    _log_batch_size = 10

    def __init__(
        self, config: models.Config, gd_client: client.GoogleDriveAnyClientType = None
    ) -> None:
        if not gd_client:
            gd_client = client.GoogleDriveClient(config)

        self._config = config
        self._client = gd_client
        self._api = interact.GoogleDriveApi(config, gd_client)
        api = self._api
        self._personal_container = interact.GoogleDriveContainer(
            google_drive_api=api,
            collection_type=api.collection_type_user,
            collection_name=api.collection_name_my_drive,
            collection_id=api.config.personal_account_email,
            collection_top_id=api.config.personal_account_top_folder_id,
        )
        self._business_container = interact.GoogleDriveContainer(
            google_drive_api=api,
            collection_type=api.collection_type_domain,
            collection_name=api.config.business_account_shared_drive,
            collection_id=api.config.business_account_domain,
            collection_top_id=api.config.business_account_top_folder_id,
        )

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
