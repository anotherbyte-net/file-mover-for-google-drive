from file_mover_for_google_drive.common import models, client, interact


class BaseManage:
    def __init__(self, config: models.Config, google_drive_client=None):
        if not google_drive_client:
            google_drive_client = client.GoogleDriveClient(config)

        self._config = config
        self._client = google_drive_client
        self._api = interact.GoogleDriveApi(config, google_drive_client)
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

    def run(self):
        raise NotImplementedError()
