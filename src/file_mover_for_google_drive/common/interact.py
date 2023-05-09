"""The Google Drive API interaction classes."""

import datetime
import itertools
import json
import logging
import typing

from googleapiclient import discovery, http

from file_mover_for_google_drive.common import models, client, utils

logger = logging.getLogger(__name__)


class GoogleDriveApi:
    """Provides access to the Google Drive API v3.
    Uses a client to make requests using the API.
    """

    # Refs:
    # https://developers.google.com/drive/api/quickstart/python
    # https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.html
    # https://developers.google.com/drive/api/v3/reference

    # NOTE: Usage limit is 20,000 requests in 100 seconds (200 requests per second).
    # https://developers.google.com/drive/api/guides/limits

    def __init__(self, config: models.ConfigProgram, gd_client: client.GoogleApiClient):
        """
        Create a new Google Drive API instance.

        Args:
            config: The program configuration.
            gd_client: The Google Drive client.
        """
        self._config = config
        self._client = gd_client

    @property
    def config(self) -> models.ConfigProgram:
        """
        Get the program configuration.

        Returns:
            The program configuration.
        """
        return self._config

    @property
    def client(self) -> discovery.Resource:
        """
        Get the Google Drive client.

        Returns:
            The Google Drive client.
        """
        if not self._client:
            raise ValueError("No client available.")
        return self._client.client()

    def files_get(self, *args: tuple[typing.Any], **kwargs) -> http.HttpRequest:
        """
        Create a file get operation.

        Args:
            *args: The placed arguments.
            **kwargs: The named arguments.

        Returns:
            A file get operation.
        """
        return self.client.files().get(*args, **kwargs)

    def files_list(self, *args: tuple[typing.Any], **kwargs) -> http.HttpRequest:
        """
        Create a file list operation.

        Args:
            *args: The placed arguments.
            **kwargs: The named arguments.

        Returns:
            A file list operation.
        """
        return self.client.files().list(*args, **kwargs)

    def files_create(self, *args: tuple[typing.Any], **kwargs) -> http.HttpRequest:
        """
        Create a file create operation.

        Args:
            *args: The placed arguments.
            **kwargs: The named arguments.

        Returns:
            A file create operation.
        """
        return self.client.files().create(*args, **kwargs)

    def files_copy(self, *args: tuple[typing.Any], **kwargs):
        return self.client.files().copy(*args, **kwargs)

    def files_update(self, *args: tuple[typing.Any], **kwargs) -> http.HttpRequest:
        return self.client.files().update(*args, **kwargs)

    def permissions_delete(
        self, *args: tuple[typing.Any], **kwargs
    ) -> http.HttpRequest:
        return self.client.permissions().delete(*args, **kwargs)

    def permissions_update(
        self, *args: tuple[typing.Any], **kwargs
    ) -> http.HttpRequest:
        return self.client.permissions().update(*args, **kwargs)

    def permissions_list(self, *args: tuple[typing.Any], **kwargs) -> http.HttpRequest:
        return self.client.permissions().list(*args, **kwargs)

    def execute_single(self, request: http.HttpRequest) -> typing.Mapping:
        """Execute an operation that returns a single response.

        Args:
            request: The request to execute.

        Returns:
            The response of the operation.
        """

        return self._do_execute(request)

    def execute_files_list(
        self, request: http.HttpRequest
    ) -> typing.Iterable[typing.Mapping]:
        """Execute an operation that returns a list of files.

        Args:
            request: The request to execute.

        Returns:
            An iterable of zero, one, or more file items.
        """

        page_count = 0
        while request is not None:
            page_count += 1

            response = self._do_execute(request)

            if not response:
                raise ValueError(
                    f"Expected a response for request '{self._request_display(request)}'."
                )

            response_items = response.get("files", [])

            logger.debug(
                "Processing page %s with %s items from '%s'.",
                page_count,
                len(response_items),
                self._request_display(request),
            )

            for entry_data in response_items:
                yield entry_data

            request = self.client.files().list_next(request, response)

    def execute_permissions_list(
        self, request: http.HttpRequest
    ) -> typing.Iterable[typing.Mapping]:
        """Execute an operation that returns a list of permissions.

        Args:
            request: The request to execute.

        Returns:
            An iterable of zero, one, or more permission items.
        """

        page_count = 0
        while request is not None:
            page_count += 1

            response = self._do_execute(request)

            if not response:
                raise ValueError(
                    f"Expected a response for request '{self._request_display(request)}'."
                )

            response_items = response.get("permissions", [])

            logger.debug(
                "Processing page %s with %s items from '%s'.",
                page_count,
                len(response_items),
                self._request_display(request),
            )

            for permission_data in response_items:
                yield permission_data

            request = self.client.permissions().list_next(request, response)

    def execute_batch(
        self,
        requests: list[http.HttpRequest],
        callback: typing.Callable[
            [str, typing.Any, typing.Optional[http.HttpError]], None
        ],
    ) -> None:
        """Execute a batch of operations.

        Args:
            requests: The requests to execute as a batch.
            callback: The callback for the result of each request.

        Returns:
            None
        """

        # https://developers.google.com/drive/api/guides/performance#batch-requests
        # https://developers.google.com/drive/api/guides/manage-sharing#change-multiple-permissions

        # Batch requests with more than 100 calls may result in an error.
        # There is an 8000-character limit on the length
        # of the URL for each inner request.
        # Currently, Google Drive does not support batch operations for media,
        # either for upload or download.
        operations_per_batch = 100
        for index, operations_group in enumerate(
            self._batched(requests, operations_per_batch)
        ):
            batch = self.client.new_batch_http_request(callback=callback)
            for operation in operations_group:
                if operation:
                    batch.add(operation)

            try:
                logger.debug(
                    "Sending batch %s with %s operations.", index + 1, len(batch)
                )
                self._do_execute(batch)
                logger.debug("Sent batch %s.", index + 1)
            except http.HttpError as error:
                logger.error(
                    "An error occurred in batch %s: %s", index + 1, error, exc_info=True
                )

    def _do_execute(self, request) -> typing.Mapping:
        """Send a request and obtain the response.

        Args:
            request: The request to send.

        Returns:
            The response.
        """
        response = request.execute(num_retries=self._config.num_retries)
        # self._write_request_response(request, response)

        return response

    def _write_request_response(self, request, response) -> None:
        file_date_str = datetime.datetime.now().isoformat(
            sep="-", timespec="microseconds"
        )
        file_date_str = file_date_str.replace(":", "-")

        dir_path = utils.get_test_resources()

        write_path = dir_path / "raw-req-res" / f"{file_date_str}-response.json"
        write_path.parent.mkdir(exist_ok=True, parents=True)

        data = {
            "request": {
                "method": request.method,
                "body": request.body,
                "methodId": request.methodId,
                "uri": request.uri,
            },
            "response": response,
        }

        with open(write_path, "wt", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _batched(
        self,
        iterable: typing.Iterable[http.HttpRequest],
        count: int = 1,
        fill_value: typing.Any = None,
    ) -> typing.Iterable[typing.Iterable[http.HttpRequest]]:
        """Collect data into fixed-length chunks or blocks.

        Args:
            iterable: The iterables to break into batches.
            count: The number of items per batch.
            fill_value: The value to fill shorter batches.

        Returns:
            An iterable of batches.
        """

        # e.g. _batched('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        # https://docs.python.org/3.5/library/itertools.html#itertools-recipes
        args = [iter(iterable)] * count
        return itertools.zip_longest(*args, fillvalue=fill_value)

    def _request_display(self, request: http.HttpRequest) -> str:
        """Build the display text for a request.

        Args:
            request: The request to display.

        Returns:
            The text representing the request.
        """
        if isinstance(request, http.HttpRequest):
            return (
                f"[{request.__class__.__name__}] {request.method}: {request.methodId}"
            )
        return f"[{request.__class__.__name__}] {str(request)}"


class GoogleDriveContainer:
    """
    Allows for useful interactions
    with a particular Google Drive 'My Drive' or 'Shared Drive'.
    Builds requests that can be executed using a Google Drive Actions instance.
    """

    def __init__(self, google_drive_api: GoogleDriveApi, account: models.ConfigAccount):
        """Create a new Google Drive container instance.

        Args:
            google_drive_api: A Google Drive Api instance.
            account: The Google Drive account
        """
        self._api = google_drive_api
        self._account = account

        self._entry_fields = models.GoogleDriveEntry.required_properties()

    @property
    def api(self):
        return self._api

    def _files_list_params(self, query: str):
        fields = f"nextPageToken,files({self._entry_fields})"
        params = {
            "spaces": "drive",
            "q": query,
            "fields": fields,
            "pageSize": 1000,
            "orderBy": "folder,name",
        }

        account_type = self._account.account_type
        account_type_personal = models.GoogleDriveAccountTypeOptions.PERSONAL
        account_type_business = models.GoogleDriveAccountTypeOptions.BUSINESS

        if account_type == account_type_personal:
            params["corpora"] = "user"
            params["includeItemsFromAllDrives"] = False
            params["supportsAllDrives"] = False

        elif account_type == account_type_business:
            params["corpora"] = "drive"
            params["driveId"] = self._account.drive_id
            params["includeItemsFromAllDrives"] = True
            params["supportsAllDrives"] = True

        else:
            raise ValueError(f"Unknown account type '{account_type}'.")

        return params

    def record_copy(
        self,
        original_entry: models.GoogleDriveEntry,
        new_entry: models.GoogleDriveEntry,
    ) -> http.HttpRequest:
        """Add a property to the original entry to record the id of the new entry."""

        entry_id = original_entry.entry_id
        key = models.GoogleDrivePropertyKeyOptions.CUSTOM_COPY_FILE_ID.value
        body = {
            "properties": {
                **original_entry.properties_shared,
                key: new_entry.entry_id,
            }
        }
        fields = self._entry_fields
        operation = self._api.files_update(fileId=entry_id, body=body, fields=fields)
        return operation

    def update_properties(
        self, entry: models.GoogleDriveEntry, all_props: typing.Mapping
    ) -> http.HttpRequest:
        entry_id = entry.entry_id
        body = {"properties": {**all_props}}
        fields = self._entry_fields
        operation = self._api.files_update(fileId=entry_id, body=body, fields=fields)
        return operation

    def create_folder(
        self, entry: models.GoogleDriveEntry, new_parent_id: str
    ) -> http.HttpRequest:
        """
        Create a new folder that is a copy of an existing folder,
        without the original folder's contents.
        """

        if not entry:
            raise ValueError("Must provide entry.")
        if not new_parent_id:
            raise ValueError("Must provide new parent.")

        body = {
            "createdTime": entry.date_created.isoformat(timespec="microseconds"),
            "modifiedTime": entry.date_modified.isoformat(timespec="microseconds"),
            "name": entry.name,
            "parents": [new_parent_id],
            "mimeType": models.GoogleDriveEntry.mime_type_dir(),
            "properties": {
                models.GoogleDrivePropertyKeyOptions.CUSTOM_ORIGINAL_FILE_ID.value: entry.entry_id
            },
        }
        fields = self._entry_fields

        operation = self._api.files_create(body=body, fields=fields)
        return operation

    def get_entry(self, entry_id: str) -> http.HttpRequest:
        """Get an entry by id."""

        params: dict[str, typing.Any] = {
            "fileId": entry_id,
            "fields": self._entry_fields,
        }

        account_type = self._account.account_type
        account_type_business = models.GoogleDriveAccountTypeOptions.BUSINESS

        if account_type == account_type_business:
            params["supportsAllDrives"] = True

        operation = self._api.files_get(**params)
        return operation

    def get_entries_by_property(self, key: str, value: str) -> http.HttpRequest:
        """
        Iterate over entries that have a property
        matching the given key and value.
        """

        kv_str = f"key='{key}' and value='{value}'"
        query = f"properties has {{ {kv_str} }} and trashed=false"
        params = self._files_list_params(query)

        operation = self._api.files_list(**params)
        return operation

    def get_children(self, folder_id: str) -> http.HttpRequest:
        """Get the child entries of the given folder with the given id."""

        # NOTE: It looks like it is not possible to filter using a folder id?
        #       Try it gives 'invalid query' error.
        # query_folder_type = "mimeType='application/vnd.google-apps.folder'"
        # query_folder_id = f"id = '{top_folder_id}'"

        query = f"'{folder_id}' in parents and trashed=false"
        params = self._files_list_params(query)

        operation = self._api.files_list(**params)
        return operation

    def delete_permission(self, entry_id: str, permission_id: str) -> http.HttpRequest:
        """Delete a permission."""
        operation = self._api.permissions_delete(
            fileId=entry_id, permissionId=permission_id
        )
        return operation

    def delete_permissions(
        self, entry: models.GoogleDriveEntry
    ) -> list[http.HttpRequest]:
        """Delete permissions for entry that are not the owner or current user."""

        permission_user = models.GoogleDrivePermissionTypeOptions.USER
        permission_anyone = models.GoogleDrivePermissionTypeOptions.ANYONE
        role_owner = models.GoogleDrivePermissionRoleOptions.OWNER.value

        operations = []
        for permission in entry.permissions_all:
            is_owner = permission.role == role_owner
            is_anyone = permission.entry_type == permission_anyone
            is_user = permission.entry_type == permission_user
            is_current_user = permission.user_email == self._account.account_id

            if is_owner or (is_user and is_current_user):
                logger.debug('Keep permission: "%s".', str(permission))

            elif is_anyone or (is_user and not is_current_user):
                operation = self.delete_permission(entry.entry_id, permission.entry_id)
                operations.append(operation)

            else:
                raise ValueError(f'Don\'t know about permission "{str(permission)}".')

        return operations

    def rename_entry(
        self, entry: models.GoogleDriveEntry, new_name: str
    ) -> http.HttpRequest:
        """Rename the file or folder."""

        if not new_name:
            raise ValueError(f"No new name given for file id '{entry.entry_id}'.")

        # NOTE: Tried to update originalFilename, but that does not seem to be saved.
        #       The old originalFilename is always returned after updating.

        entry_id = entry.entry_id
        body = {"name": new_name}
        fields = self._entry_fields
        operation = self._api.files_update(fileId=entry_id, body=body, fields=fields)
        return operation

    def copy_file(
        self, entry: models.GoogleDriveEntry, parent_id: str
    ) -> http.HttpRequest:
        """
        Copy a file that is not owned to
        create a copy that is owned by the current user.
        Must be copied within a personal account (i.e. My Drive).
        """

        entry_id = entry.entry_id
        body = {
            "createdTime": entry.date_created.isoformat(timespec="microseconds"),
            "modifiedTime": entry.date_modified.isoformat(timespec="microseconds"),
            "description": entry.description,
            "name": entry.name,
            "parents": [parent_id],
            "properties": {
                models.GoogleDrivePropertyKeyOptions.CUSTOM_ORIGINAL_FILE_ID.value: entry.entry_id
            },
            "mimeType": entry.mime_type,
        }
        fields = self._entry_fields
        operation = self._api.files_copy(fileId=entry_id, body=body, fields=fields)
        return operation

    def move_entry(
        self, entry: models.GoogleDriveEntry, parent_id: str
    ) -> http.HttpRequest:
        """
        Move the file from one folder to another folder within the one account.
        """

        entry_id = entry.entry_id
        fields = self._entry_fields
        operation = self._api.files_update(
            fileId=entry_id,
            removeParents=entry.parent_id,
            addParents=parent_id,
            fields=fields,
        )
        return operation

    def get_permissions(self, entry_id: str) -> http.HttpRequest:
        """Get the permissions for a file or folder or shared drive."""

        permission_props = [
            "id",
            "type",
            "emailAddress",
            "domain",
            "role",
            "displayName",
            "permissionDetails",
        ]

        params = {
            "fileId": entry_id,
            "fields": f"nextPageToken,permissions({','.join(permission_props)})",
            "useDomainAdminAccess": False,
        }

        account_type_business = models.GoogleDriveAccountTypeOptions.BUSINESS
        if self._account.account_type == account_type_business:
            params["supportsAllDrives"] = True

        operation = self._api.permissions_list(**params)
        return operation


class GoogleDriveActions:
    """
    Interacts with a particular Google 'My Drive' or 'Shared Drive'
    by executing requests that have been built.
    """

    def __init__(self, container: GoogleDriveContainer):
        self._container = container

    @property
    def container(self) -> GoogleDriveContainer:
        return self._container

    def get_descendants(
        self, folder_id: str
    ) -> typing.Generator[models.GoogleDriveEntry, typing.Any, None]:
        """
        Get all descendants of the given folder.
        In other words, get the files in the folder,
        then the files in each sub-folder, recursively.
        """

        container = self._container
        api = container.api

        request = container.get_children(folder_id)
        for entry_data in api.execute_files_list(request):
            # provide the children of folder_id
            entry = self._get_entry(entry_data)
            yield entry

            if entry.entry_id != folder_id and entry.is_dir:
                # provide the children of folders in folder_id
                for entry_desc in self.get_descendants(entry.entry_id):
                    yield entry_desc

    def get_entry(self, entry_id: str) -> models.GoogleDriveEntry:
        """Get the details of a file or folder."""

        container = self.container
        api = container.api

        request = container.get_entry(entry_id)
        entry_data = api.execute_single(request)
        entry = self._get_entry(entry_data)

        return entry

    def get_pair_copy_entry(
        self, entry: models.GoogleDriveEntry
    ) -> typing.Optional[models.GoogleDriveEntry]:
        """
        For an original (un-owned), get a copy if it exists.
        For a copy (owned) file, get the original.

        Works in personal accounts only.
        """

        container = self._container
        api = container.api
        config = api.config
        account = config.account

        account_type_personal = models.GoogleDriveAccountTypeOptions.PERSONAL
        if account.account_type != account_type_personal:
            raise ValueError(
                f"Entry pairs only work in '{account_type_personal}' accounts, "
                f"not '{account.account_type}'."
            )

        account_id = account.account_id
        entry_is_owned = entry.is_owned_by(account_id)

        key_copy = models.GoogleDrivePropertyKeyOptions.CUSTOM_COPY_FILE_ID.value
        key_orig = models.GoogleDrivePropertyKeyOptions.CUSTOM_ORIGINAL_FILE_ID.value

        if entry_is_owned:
            # if the entry is owned (might be a copy),
            # see if there is an original that is not owned
            prop_key = key_copy

            # check the found original (unowned) entry's property
            pair_key = key_orig

        else:
            # if the entry is not owned (the original),
            # see if there is a copy that is owned
            prop_key = key_orig

            # check the found copy (owned) entry's property
            pair_key = key_copy

        if not prop_key:
            return None

        # get the pair
        prop_value = entry.entry_id
        request = container.get_entries_by_property(prop_key, prop_value)

        entries = []
        for entry_data in api.execute_files_list(request):
            entry_item = self._get_entry(entry_data)
            entries.append(entry_item)

        entry_count = len(entries)
        if entry_count > 1:
            raise ValueError(
                f"More than one match for property '{prop_key}={prop_value}'."
            )

        if entry_count < 1:
            return None

        # found the pair
        pair_entry = entries[0]

        # check that the pair has the expected id stored in the entry
        expected_pair_id = entry.properties_shared.get(pair_key)
        actual_pair_id = pair_entry.entry_id

        if expected_pair_id != actual_pair_id:
            raise ValueError(
                f"Found pair does not have the expected property. "
                f"Entry {str(entry)}. "
                f"Pair {str(pair_entry)}. "
                f"Expected '{pair_key}={expected_pair_id}'. "
                f"Actual '{pair_key}={actual_pair_id}'."
            )

        return pair_entry

    def create_folder(
        self, entry: models.GoogleDriveEntry
    ) -> tuple[models.GoogleDriveEntry, models.GoogleDriveEntry]:
        """Create a new folder that is a copy of an existing folder,
        without the original folder's contents.

        Args:
            entry: The entry to use as the basis for creating a new folder.

        Returns:
            The new folder object.
        """
        container = self._container
        request_new = container.create_folder(entry, entry.parent_id)
        response_new = container.api.execute_single(request_new)
        new_entry = self._get_entry(response_new)

        # update the entry to add the property
        request_exist = container.record_copy(entry, new_entry)
        response_exist = container.api.execute_single(request_exist)
        entry = self._get_entry(response_exist)

        return new_entry, entry

    def copy_file(
        self, entry: models.GoogleDriveEntry
    ) -> tuple[models.GoogleDriveEntry, models.GoogleDriveEntry]:
        """Copy a file that is not owned to create a copy
        that is owned by the current user.
        Must be copied within a personal account (i.e. My Drive).

        Args:
            entry: The entry to copy.

        Returns:
            The new file object.
        """
        container = self._container
        request_new = container.copy_file(entry, entry.parent_id)
        response_new = container.api.execute_single(request_new)
        new_entry = self._get_entry(response_new)

        # update the entry to add the property
        request_exist = container.record_copy(entry, new_entry)
        response_exist = container.api.execute_single(request_exist)
        entry = self._get_entry(response_exist)

        return new_entry, entry

    def rename_entry(
        self, entry: models.GoogleDriveEntry, name: str
    ) -> models.GoogleDriveEntry:
        """Rename the file or folder.

        Args:
            entry: The entry to rename.
            name: The new name.

        Returns:
            The updated entry object.
        """
        container = self._container
        request = container.rename_entry(entry, name)
        response = container.api.execute_single(request)
        entry = self._get_entry(response)
        return entry

    def delete_permission(self, entry_id: str, permission_id: str) -> None:
        """

        Args:
            entry_id:
            permission_id:

        Returns:

        """
        container = self._container
        request = container.delete_permission(entry_id, permission_id)
        container.api.execute_single(request)

    def move_entry(self, entry: models.GoogleDriveEntry, new_parent_id: str):
        """Move a file from one folder to another folder.

        Args:
            entry: The file to move.
            new_parent_id: move the file into this folder id.

        Returns:
            The update file object.
        """
        container = self._container
        request = container.move_entry(entry, new_parent_id)
        response = container.api.execute_single(request)
        entry = self._get_entry(response)
        return entry

    def update_properties(
        self, entry: models.GoogleDriveEntry, all_props: typing.Mapping
    ):
        container = self._container
        request = container.update_properties(entry, all_props)
        response = container.api.execute_single(request)
        entry = self._get_entry(response)
        return entry

    def _get_entry(self, entry_data: typing.Mapping):
        container = self._container
        api = container.api
        config = api.config
        account = config.account

        entry_id = entry_data.get("id")
        if not entry_id:
            raise ValueError("Require an entry id to get the entry details.")

        is_trashed = entry_data.get("trashed")
        if is_trashed is not False:
            raise ValueError("Cannot work with an entry that is trashed.")

        # get the full permissions list for the entry
        request = container.get_permissions(entry_id)
        permissions_list = []
        for permission_data in api.execute_permissions_list(request):
            permissions_list.append(
                models.GoogleDrivePermission.load_data(permission_data)
            )

        # create the entry object
        params = {
            **entry_data,
            "fileMoverExtraAccount": account,
            "fileMoverExtraPermissions": permissions_list,
        }
        entry = models.GoogleDriveEntry.load_data(params)
        return entry
