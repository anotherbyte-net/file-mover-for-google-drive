import logging
import typing

from file_mover_for_google_drive.common import models, client, manage, report

logger = logging.getLogger(__name__)


class TidyProperties(manage.BaseManage):
    """
    Remove properties added by this app.
    """

    def __init__(
        self,
        config: models.ConfigProgram,
        gd_client: typing.Optional[client.GoogleApiClient] = None,
    ) -> None:
        """Create a new Tidy Properties instance."""
        super().__init__(config=config, allow_modify=True, gd_client=gd_client)

    def run(self) -> bool:
        """Run the 'tidy-properties' action."""

        config = self._config
        account = config.account

        logger.info(
            "Tidy properties for %s account '%s'.",
            account.account_type.name,
            account.account_id,
        )

        result = self._iterate_entries(self.process_one)
        return result

    def process_one(self, entry: models.GoogleDriveEntry) -> None:
        """Process one entry."""

        actions = self._actions
        cache = self._cache

        cache.add(entry)

        logger.info("Processing %s.", str(entry))

        new_props = {**entry.properties_shared}

        remove_keys = [
            models.GoogleDrivePropertyKeyOptions.CUSTOM_ORIGINAL_FILE_ID.value,
            models.GoogleDrivePropertyKeyOptions.CUSTOM_COPY_FILE_ID.value,
            "CustomOriginalFileId",
            "CustomCopyFileId",
            "CustomPreviousAccountId",
            "CustomNewAccountId",
        ]

        for remove_key in remove_keys:
            if remove_key in new_props:
                new_props[remove_key] = None

        if entry.properties_shared == new_props:
            return None

        new_entry = actions.update_properties(entry, new_props)

        logger.info(
            f"Updated properties for {str(entry)}. "
            f"Old '{entry.properties_shared}'. "
            f"New'{new_entry.properties_shared}'."
        )
