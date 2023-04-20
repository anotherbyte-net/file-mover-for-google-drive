import re
import logging
import typing

from google.auth.transport.requests import Request  # noqa: I900
from google.oauth2.credentials import Credentials  # noqa: I900
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build  # noqa: I900
from googleapiclient.errors import HttpError  # noqa: I900

from file_mover_for_google_drive.common import models

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """A client that provides access to Google Drive."""

    def __init__(self, config: models.Config):
        """Create a new Google Drive Client instance."""
        self._config = config

        self._client = None
        self._scopes = [
            # for listing file metadata
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            # for permission delete, file copy, file update, file create
            # "https://www.googleapis.com/auth/drive",
        ]

    def _authorise(self):
        """Authorise access to the Google Drive API."""
        creds = None

        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if self._config.auth_token_file.exists():
            logger.info("Using credentials from token.json file.")
            creds = Credentials.from_authorized_user_file(
                str(self._config.auth_token_file), self._scopes
            )

        # If there are no (valid) credentials available, prompt the user to log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Requesting new credentials.")
                creds.refresh(Request())
            else:
                logger.info("Starting authorisation flow.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._config.auth_credentials_file), self._scopes
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            logger.info("Saving credentials to token.json file.")
            self._config.auth_token_file.write_text(creds.to_json())

        return creds

    def client(self):
        """Get the client."""
        if self._client:
            logger.debug("Using existing client.")
            return self._client

        creds = self._authorise()

        try:
            # NOTE: Tried to use the MemoryCache,
            # but the cache does not seem to be used?
            # https://github.com/googleapis/google-api-python-client/issues/325#issuecomment-274349841
            build_args = ["drive", "v3"]
            params = {"cache_discovery": False, "credentials": creds}

            self._client = build(*build_args, **params)

            logger.info("Created new client.")
        except HttpError as error:
            logger.error("An error occurred %s", error, exc_info=True)

        return self._client


class LocalInMemoryClient:
    """A client that stores files and folders in-memory for testing."""

    def __init__(self, raw: dict):
        """Create a new Local in-memory client."""
        self._raw = raw
        self._client = LocalInMemoryStore(self._raw)

    def client(self):
        """Get the client instance."""
        return self._client


class LocalInMemoryOperationStore:
    def __init__(self, change, *args, **kwargs):
        self._change = change
        self._args = args
        self._kwargs = kwargs

    def execute(self, *args, **kwargs):
        args = (*self._args, *args)
        kwargs = {**self._kwargs, **kwargs}
        return self._change(*args, **kwargs)

    def __str__(self):
        change_name = self._change.__name__
        kwargs_keys = ",".join(sorted(self._kwargs.keys()))
        return f"{change_name}: {kwargs_keys}"


class LocalInMemoryPermissionsStore:
    def __init__(self, client: "LocalInMemoryStore"):
        self._client = client

    def create(self, *args, **kwargs):
        return LocalInMemoryOperationStore(self._create, *args, **kwargs)

    def _create(self, *args, **kwargs):
        raise ValueError(str(args) + str(kwargs))

    def update(self, *args, **kwargs):
        return LocalInMemoryOperationStore(self._update, *args, **kwargs)

    def _update(self, *args, **kwargs):
        raise ValueError(str(args) + str(kwargs))

    def delete(self, *args, **kwargs):
        return LocalInMemoryOperationStore(self._delete, *args, **kwargs)

    def _delete(self, *args, **kwargs):
        raise ValueError(str(args) + str(kwargs))


class LocalInMemoryFilesStore:
    def __init__(self, client: "LocalInMemoryStore"):
        self._client = client

    def get(self, *args, **kwargs):
        return LocalInMemoryOperationStore(self._get, *args, **kwargs)

    def _get(self, *args, **kwargs):
        args_list = sorted(args)
        kwargs_list = sorted(kwargs.keys())
        client = self._client

        entry_id: str = kwargs.get("fileId", "")
        if not entry_id:
            raise ValueError("Must provide file id.")

        if not args_list and kwargs_list == ["fields", "fileId", "num_retries"]:
            return client._get(entry_id)

        raise ValueError(str(args) + str(kwargs))

    def list(self, *args, **kwargs):
        return LocalInMemoryOperationStore(self._list, *args, **kwargs)

    def _list(self, *args, **kwargs):
        args_list = sorted(args)
        kwargs_list = sorted(kwargs.keys())
        client = self._client

        # gather params
        q_children = re.compile(
            r"^'(?P<id>.*?)' in parents and trashed=false$",
        )
        q_properties = re.compile(
            r"^properties has { key='(?P<key>.*?)' and "
            r"value='(?P<value>.*?)' } and trashed=false$",
        )

        # corpora = kwargs.get("corpora", "")
        # spaces = kwargs.get("spaces", "")
        q = kwargs.get("q", "")
        # fields = kwargs.get("fields", "")
        # supports_all_drives = kwargs.get("supportsAllDrives")
        # include_items_from_all_drives = kwargs.get("includeItemsFromAllDrives")
        # page_size = kwargs.get("pageSize")
        # page_token = kwargs.get("pageToken")
        # order_by = kwargs.get("orderBy")
        # num_retries = kwargs.get("num_retries")

        match_children = q_children.match(q)
        match_properties = q_properties.match(q)

        # build response

        # children of a folder
        expected_keys = sorted(
            [
                "spaces",
                "q",
                "fields",
                "pageSize",
                "orderBy",
                "supportsAllDrives",
                "includeItemsFromAllDrives",
                "corpora",
                "num_retries",
            ]
        )
        if not args_list and kwargs_list == expected_keys and match_children:
            parent_id = match_children.group("id")
            children = client._get_children(parent_id)
            return {"kind": "drive#fileList", "files": children}

        # search by entry property
        expected_keys = sorted(
            [
                "spaces",
                "q",
                "fields",
                "pageSize",
                "orderBy",
                "supportsAllDrives",
                "includeItemsFromAllDrives",
                "corpora",
                "num_retries",
            ]
        )
        if not args_list and kwargs_list == expected_keys and match_properties:
            prop_key = match_properties.group("key")
            prop_value = match_properties.group("value")
            items = client._get_by_props(prop_key, prop_value)
            return {"kind": "drive#fileList", "files": items}

        raise ValueError(str(args) + str(kwargs))

    def update(self, *args, **kwargs):
        return LocalInMemoryOperationStore(self._update, *args, **kwargs)

    def _update(self, *args, **kwargs):
        # args_list = list(args)
        # kwargs_list = list(kwargs.keys())
        client = self._client

        body = kwargs.get("body", {})
        # properties = body.get("properties", {})
        custom_copy_file_id = body.get("CustomCopyFileId")
        remove_parents = kwargs.get("removeParents", "").split(",")
        add_parents = kwargs.get("addParents", "").split(",")
        # supports_team_drives = kwargs.get("supportsTeamDrives")
        # supports_all_drives = kwargs.get("supportsAllDrives")
        file_id: str = kwargs.get("fileId", "")
        if not file_id:
            raise ValueError("Must provide file id.")

        if body and remove_parents and add_parents:
            entry = client._get(file_id)
            if not entry:
                raise ValueError(str(args) + str(kwargs))
            if custom_copy_file_id:
                entry["properties"]["CustomCopyFileId"] = custom_copy_file_id

            if entry.get("parents") != remove_parents:
                raise ValueError(str(args) + str(kwargs))

            entry["parents"] = [
                p for p in entry["parents"] + add_parents if p not in remove_parents
            ]
            return entry

        raise ValueError(str(args) + str(kwargs))

    def list_next(self, *args, **kwargs):  # noqa: U100
        """For the local tests, list_next always acts as if there is no more items."""
        return None
        # return LocalInMemoryOperationStore(self._list_next, *args, **kwargs)

    def _list_next(self, *args, **kwargs):
        # args_list = list(args)
        kwargs_list = list(kwargs.keys())

        if (
            len(args) == 2
            and isinstance(args[0], LocalInMemoryOperationStore)
            and kwargs_list == ["num_retries"]
        ):
            next_token = args[1].get("nextToken")
            if next_token:
                raise NotImplementedError()
            return None

        raise ValueError(str(args) + str(kwargs))


class LocalInMemoryStore:
    def __init__(self, raw: dict):
        self._files = LocalInMemoryFilesStore(self)
        self._permissions = LocalInMemoryPermissionsStore(self)
        self._store = raw

    def files(self):
        return self._files

    def permissions(self):
        return self._permissions

    def _get(self, entry_id: str):
        for item in self._store:
            if item.get("id") == entry_id:
                return item
        return None

    def _get_children(self, entry_id: str):
        result = []
        for item in self._store:
            if entry_id in item.get("parents"):
                result.append(item)
        return result

    def _get_by_props(self, prop_key: str, prop_value: str):
        result = []
        for item in self._store:
            properties = item.get("properties")
            value = properties.get(prop_key)
            if value == prop_value:
                result.append(item)
        return result

    def _get_structure(self):
        return self._store

    def _update_structure(self, raw):
        self._store = raw


GoogleDriveAnyClientType = typing.Optional[
    typing.Union[GoogleDriveClient, LocalInMemoryClient]
]
