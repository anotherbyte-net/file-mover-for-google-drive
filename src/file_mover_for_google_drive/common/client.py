import logging
import typing

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib import flow
from googleapiclient import discovery, errors

from file_mover_for_google_drive.common import models

logger = logging.getLogger(__name__)


class GoogleApiClient:
    """A client that provides access to a Google API."""

    def __init__(
        self,
        config: models.ConfigProgram,
        scopes: list[str],
        client_args: typing.Mapping,
        existing_client: typing.Optional[discovery.Resource] = None,
    ):
        """Create a new Google API Client instance."""
        self._config = config
        self._scopes = scopes
        self._client_args = client_args
        self._client = existing_client

    def _authorise(self):
        """Authorise access to the Google API."""
        creds = None

        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if self._config.auth.token_file.exists():
            logger.debug("Using existing token.")
            creds = Credentials.from_authorized_user_file(
                str(self._config.auth.token_file), self._scopes
            )

        # If there are no (valid) credentials available, prompt the user to log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Requesting new credentials.")
                creds.refresh(Request())
            else:
                logger.info("Starting authorisation flow.")
                flow_result = flow.InstalledAppFlow.from_client_secrets_file(
                    str(self._config.auth.credentials_file), self._scopes
                )
                creds = flow_result.run_local_server(port=0)

            # Save the credentials for the next run
            logger.info("Saving credentials to token.json file.")
            self._config.auth.token_file.write_text(creds.to_json())

        return creds

    def client(self) -> discovery.Resource:
        """Get the client."""
        if self._client:
            # logger.debug("Using existing client.")
            return self._client

        creds = self._authorise()

        try:
            params = {**self._client_args, "credentials": creds}
            self._client = discovery.build(**params)

            logger.debug("Created new client.")
        except errors.HttpError as error:
            logger.error("An error occurred %s", error, exc_info=True)

        return self._client

    @classmethod
    def get_drive_client(
        cls,
        config: models.ConfigProgram,
        scopes_additional: typing.Optional[list[str]] = None,
        client_args_additional: typing.Optional[typing.Mapping] = None,
        existing_client: typing.Optional[discovery.Resource] = None,
    ) -> "GoogleApiClient":
        scopes = [
            *(scopes_additional or []),
            # for listing file metadata
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            # for permission delete, file copy, file update, file create
            # "https://www.googleapis.com/auth/drive",
        ]
        client_args = {
            **(client_args_additional or {}),
            "serviceName": "drive",
            "version": "v3",
            # NOTE: Tried to use the MemoryCache,
            # but the cache does not seem to be used?
            # https://github.com/googleapis/google-api-python-client/issues/325#issuecomment-274349841
            "cache_discovery": False,
        }
        return GoogleApiClient(config, scopes, client_args, existing_client)
