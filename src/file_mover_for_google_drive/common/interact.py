import itertools
import logging
import typing

from googleapiclient.errors import HttpError
from googleapiclient.http import HttpRequest

from file_mover_for_google_drive.common import models

logger = logging.getLogger(__name__)


class GoogleDriveApi:
    """
    Provides access to the Google Drive API v3.
    Uses a client to make requests using the API.
    """

    # https://developers.google.com/drive/api/quickstart/python
    # https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.html
    # https://developers.google.com/drive/api/v3/reference

    # NOTE: Usage limit is 20,000 requests in 100 seconds (200 requests per second).
    # https://developers.google.com/drive/api/guides/limits

    collection_type_user = "user"
    collection_type_domain = "domain"
    collection_name_my_drive = "My Drive"

    role_owner = "owner"
    role_editor = "writer"
    role_commenter = "commenter"
    role_viewer = "reader"

    # user & group require 'emailAddress' to be set
    # domain requires 'domain' to be set
    permission_user = "user"
    permission_group = "group"
    permission_domain = "domain"
    permission_anyone = "anyone"

    # only for 'user' type and not in shared drive
    permission_pending_owner = "pendingOwner"

    def __init__(self, config: models.Config, client):
        self._config = config
        self._client = client

    @property
    def config(self):
        return self._config

    @property
    def client(self):
        return self._client.client()

    def files_get(self, *args, **kwargs) -> HttpRequest:
        return self.client.files().get(*args, **kwargs)

    def files_list(self, *args, **kwargs) -> HttpRequest:
        return self.client.files().list(*args, **kwargs)

    def files_create(self, *args, **kwargs) -> HttpRequest:
        return self.client.files().create(*args, **kwargs)

    def files_copy(self, *args, **kwargs):
        return self.client.files().copy(*args, **kwargs)

    def files_update(self, *args, **kwargs) -> HttpRequest:
        return self.client.files().update(*args, **kwargs)

    def permissions_delete(self, *args, **kwargs) -> HttpRequest:
        return self.client.permissions().delete(*args, **kwargs)

    def permissions_update(self, *args, **kwargs) -> HttpRequest:
        return self.client.permissions().update(*args, **kwargs)

    def permissions_list(self, *args, **kwargs) -> HttpRequest:
        return self.client.permissions().list(*args, **kwargs)

    def execute_single(self, operation):
        """Execute an operation that returns a single result."""

        result = operation.execute(num_retries=self._config.num_retries)
        return result

    def execute_files_list(self, request):
        """Execute an operation that returns a list of files."""

        page_count = 0
        while request is not None:
            page_count += 1
            logger.debug(
                "Getting page %s of results using '%s'.",
                page_count,
                self._request_display(request),
            )

            response = request.execute(num_retries=self._config.num_retries)

            if not response:
                raise ValueError("Expected a response.")

            for entry_data in response.get("files", []):
                yield entry_data

            request = self.client.files().list_next(request, response)

    def execute_permissions_list(self, request):
        """Execute an operation that returns a list of permissions."""

        page_count = 0
        while request is not None:
            page_count += 1
            logger.debug(
                "Getting page %s of results using '%s'.",
                page_count,
                self._request_display(request),
            )

            response = request.execute(num_retries=self._config.num_retries)

            if not response:
                raise ValueError("Expected a response.")

            for permission_data in response.get("permissions", []):
                yield permission_data

            request = self.client.permissions().list_next(request, response)

    def execute_batch(
        self,
        operations: list,
        callback: typing.Callable[[str, typing.Any, typing.Optional[HttpError]], None],
    ):
        """Execute a batch of operations."""

        # https://developers.google.com/drive/api/guides/performance#batch-requests
        # https://developers.google.com/drive/api/guides/manage-sharing#change-multiple-permissions

        # Batch requests with more than 100 calls may result in an error.
        # There is an 8000-character limit on the length of the URL for each inner request.
        # Currently, Google Drive does not support batch operations for media, either for upload or download.
        operations_per_batch = 99
        for index, operations_group in enumerate(
            self._batched(operations, operations_per_batch)
        ):
            batch = self.client.new_batch_http_request(callback=callback)
            for operation in operations_group:
                if operation:
                    batch.add(operation)

            try:
                logger.debug(
                    "Sending batch %s with %s operations.", index + 1, len(batch)
                )
                batch.execute(num_retries=self._config.num_retries)
                logger.debug("Sent batch %s.", index + 1)
            except HttpError as error:
                logger.error(
                    "An error occurred in batch %s: %s", index + 1, error, exc_info=True
                )

    def _batched(self, iterable, count=1, fill_value=None):
        """Collect data into fixed-length chunks or blocks"""

        # e.g. _batched('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        # https://docs.python.org/3.5/library/itertools.html#itertools-recipes
        args = [iter(iterable)] * count
        return itertools.zip_longest(*args, fillvalue=fill_value)

    def _request_display(self, request):
        if isinstance(request, HttpRequest):
            return (
                f"[{request.__class__.__name__}] {request.method}: {request.methodId}"
            )
        return f"[{request.__class__.__name__}] {str(request)}"


class GoogleDriveContainer:
    """
    Allows for useful interactions
    with a particular Google Drive 'My Drive' or 'Shared Drive'.
    Builds requests that can be executed using the Google Drive API.
    """

    name_prefix_copy_of = "Copy of "
    name_prefix_copy_of_len = len(name_prefix_copy_of)

    def __init__(
        self,
        google_drive_api: GoogleDriveApi,
        collection_type: str,
        collection_name: str,
        collection_id: str,
        collection_top_id: str,
    ):
        self._api = google_drive_api
        self._collection_type = collection_type
        self._collection_name = collection_name
        self._collection_id = collection_id
        self._collection_top_id = collection_top_id

        self._entry_fields = models.GoogleDriveEntry.required_properties()

    @property
    def api(self):
        return self._api

    @property
    def collection_type(self):
        return self._collection_type

    @property
    def collection_name(self):
        return self._collection_name

    @property
    def collection_id(self):
        return self._collection_id

    @property
    def collection_top_id(self):
        return self._collection_top_id

    def _files_list_params(self, query: str):
        fields = f"nextPageToken,files({self._entry_fields})"
        params = {
            "spaces": "drive",
            "q": query,
            "fields": fields,
            "pageSize": 1000,
            "orderBy": "folder,name",
        }

        if self._collection_type == self._api.collection_type_user:
            params["corpora"] = "user"
            params["includeItemsFromAllDrives"] = False
            params["supportsAllDrives"] = False

        elif self._collection_type == self._api.collection_type_domain:
            params["corpora"] = "drive"
            params["driveId"] = self._collection_top_id
            params["includeItemsFromAllDrives"] = True
            params["supportsAllDrives"] = True

        else:
            raise ValueError(f"Unknown collection type '{self._collection_type}'.")

        return params

    def record_copy(
        self,
        original_entry: models.GoogleDriveEntry,
        new_entry: models.GoogleDriveEntry,
    ) -> HttpRequest:
        """Add a property to the original entry to record the id of the new entry."""

        entry_id = original_entry.entry_id
        body = {
            "properties": {self.api.config.custom_prop_copy_key: new_entry.entry_id}
        }
        fields = self._entry_fields
        operation = self._api.files_update(fileId=entry_id, body=body, fields=fields)
        return operation

    def create_folder(
        self, entry: models.GoogleDriveEntry, new_parent_id: str
    ) -> HttpRequest:
        """
        Create a new folder that is a copy of an existing folder,
        without the original folder's contents.
        """

        if not entry:
            raise ValueError("Must provide entry.")
        if not new_parent_id:
            raise ValueError("Must provide new parent.")

        body = {
            "createdTime": entry.date_created,
            "modifiedTime": entry.date_modified,
            "name": entry.name,
            "parents": [new_parent_id],
            "mimeType": models.GoogleDriveEntry.mime_type_dir(),
            "properties": {self.api.config.custom_prop_original_key: entry.entry_id},
        }
        fields = self._entry_fields

        operation = self._api.files_create(body=body, fields=fields)
        return operation

    def get_entry(self, entry_id: str) -> HttpRequest:
        """Get an entry by id."""

        params: dict[str, typing.Any] = {
            "fileId": entry_id,
            "fields": self._entry_fields,
        }

        if self._collection_type == self._api.collection_type_domain:
            params["supportsAllDrives"] = True

        operation = self._api.files_get(**params)
        return operation

    def get_entries_by_property(self, key: str, value: str) -> HttpRequest:
        """Iterate over entries that have a property matching the given key and value."""

        queries = [
            f"properties has {{ key='{key}' and value='{value}' }}",
            "trashed=false",
        ]
        query = " and ".join(queries)
        params = self._files_list_params(query)

        operation = self._api.files_list(**params)
        return operation

    def get_children(self, folder_id: str) -> HttpRequest:
        """Get the child entries of the given folder with the given id."""

        # NOTE: It looks like it is not possible to filter using a folder id?
        #       Try it gives 'invalid query' error.
        # query_folder_type = "mimeType='application/vnd.google-apps.folder'"
        # query_folder_id = f"id = '{top_folder_id}'"

        query = f"'{folder_id}' in parents and trashed=false"
        params = self._files_list_params(query)

        operation = self._api.files_list(**params)
        return operation

    def delete_permissions(self, entry: models.GoogleDriveEntry) -> list[HttpRequest]:
        """Delete permissions for entry that are not the owner or current user."""

        operations = []
        for permission in entry.permissions:
            is_owner = permission.role == self._api.role_owner
            is_anyone = permission.entry_type == self._api.permission_anyone
            is_user = permission.entry_type == self._api.permission_user
            is_current_user = permission.user_email == self._collection_id

            if is_owner or (is_user and is_current_user):
                logger.debug('Keep permission: "%s".', str(permission))

            elif is_anyone or (is_user and not is_current_user):
                operation = self._api.permissions_delete(
                    fileId=entry.entry_id, permissionId=permission.entry_id
                )
                operations.append(operation)

            else:
                raise ValueError(f'Don\'t know about permission "{str(permission)}".')

        return operations

    def rename_entry(
        self, entry: models.GoogleDriveEntry, new_name: str
    ) -> HttpRequest:
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

    def copy_file(self, entry: models.GoogleDriveEntry, parent_id: str) -> HttpRequest:
        """
        Copy a file that is not owned to
        create a copy that is owned by the current user.
        Must be copied within a personal collection (i.e. My Drive).
        """

        entry_id = entry.entry_id
        body = {
            "createdTime": entry.date_created,
            "modifiedTime": entry.date_modified,
            "description": entry.description,
            "name": entry.name,
            "parents": [parent_id],
            "properties": {self.api.config.custom_prop_original_key: entry.entry_id},
            "mimeType": entry.mime_type,
        }
        fields = self._entry_fields
        operation = self._api.files_copy(fileId=entry_id, body=body, fields=fields)
        return operation

    def move_file(self, entry: models.GoogleDriveEntry, parent_id: str) -> HttpRequest:
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

    def update_owner(
        self, entry: models.GoogleDriveEntry, new_parent_id: str
    ) -> HttpRequest:
        """Transfer ownership from a personal account to a business account."""

        params = {
            "fileId": entry.entry_id,
            "fields": self._entry_fields,
            "body": {
                "properties": {
                    self.api.config.custom_prop_transfer_key: entry.parent_id
                }
            },
            "removeParents": entry.parent_id,
            "addParents": new_parent_id,
        }

        if self._collection_type == self._api.collection_type_domain:
            params["supportsAllDrives"] = True

        operation = self._api.files_update(**params)
        return operation

    def get_permissions(self, entry_id: str) -> HttpRequest:
        """Get the permissions for a file or folder or shared drive."""

        params = {
            "fileId": entry_id,
            "fields": "nextPageToken,permissions(id,type,emailAddress,domain,role,displayName,permissionDetails)",
            "useDomainAdminAccess": False,
        }

        if self._collection_type == self._api.collection_type_domain:
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
    def container(self):
        return self._container

    def get_descendants(
        self, folder_id: str
    ) -> typing.Generator[models.GoogleDriveEntry, typing.Any, None]:
        """
        Get all descendants of the given folder.
        In other words, get the files in the folder, then the files in each sub-folder, recursively.
        """

        container = self._container
        api = container.api

        col_type = container.collection_type
        col_name = container.collection_name
        col_id = container.collection_id

        request = container.get_children(folder_id)
        for entry_data in api.execute_files_list(request):
            # provide the children of folder_id
            entry = models.GoogleDriveEntry(entry_data, col_type, col_name, col_id)

            # add permissions from shared drive
            if entry.collection_type == api.collection_type_domain:
                request = container.get_permissions(entry.entry_id)
                entry_shared_permissions = []
                for permission_data in api.execute_permissions_list(request):
                    entry_shared_permissions.append(
                        models.GoogleDrivePermission(permission_data)
                    )
                entry.set_shared_drive_permissions(entry_shared_permissions)

            yield entry

            if entry.entry_id != folder_id and entry.is_dir:
                # provide the children of folders in folder_id
                for entry in self.get_descendants(entry.entry_id):
                    yield entry

    def get_entry(self, entry_id: str) -> models.GoogleDriveEntry:
        """Get the details of a file or folder."""

        container = self.container
        api = container.api

        col_type = container.collection_type
        col_name = container.collection_name
        col_id = container.collection_id

        request = container.get_entry(entry_id)
        entry_data = api.execute_single(request)
        entry = models.GoogleDriveEntry(entry_data, col_type, col_name, col_id)

        # add permissions from shared drive
        if entry.collection_type == api.collection_type_domain:
            request = container.get_permissions(entry.entry_id)
            entry_shared_permissions = []
            for permission_data in api.execute_permissions_list(request):
                entry_shared_permissions.append(
                    models.GoogleDrivePermission(permission_data)
                )
            entry.set_shared_drive_permissions(entry_shared_permissions)

        return entry

    def get_pair(
        self, entry: models.GoogleDriveEntry
    ) -> typing.Optional[models.GoogleDriveEntry]:
        """
        For an original (un-owned), get a copy if it exists.
        For a copy (owned) file, get the original.
        """

        container = self._container
        api = container.api
        config = api.config

        col_type = container.collection_type
        col_name = container.collection_name
        col_id = container.collection_id

        personal_account_email = config.personal_account_email
        entry_is_owned = entry.is_owned_by(personal_account_email)

        if entry_is_owned:
            # if the entry is owned (might be a copy), see if there is an original that is not owned
            key = config.custom_prop_copy_key

        else:
            # if the entry is not owned (the original), see if there is a copy that is owned
            key = config.custom_prop_original_key

        value = entry.entry_id

        request = container.get_entries_by_property(key, value)

        entries = []
        for entry_data in api.execute_files_list(request):
            entry = models.GoogleDriveEntry(entry_data, col_type, col_name, col_id)

            # add permissions from shared drive
            if entry.collection_type == api.collection_type_domain:
                request = container.get_permissions(entry.entry_id)
                entry_shared_permissions = []
                for permission_data in api.execute_permissions_list(request):
                    entry_shared_permissions.append(
                        models.GoogleDrivePermission(permission_data)
                    )
                entry.set_shared_drive_permissions(entry_shared_permissions)

            entries.append(entry)

        entry_count = len(entries)
        if entry_count > 1:
            raise ValueError(f"More than one match for property '{key}={value}'.")
        elif entry_count == 1:
            return entries[0]
        else:
            return None


#
#

#
# def permission_remove(self, entry_id: str, permission_id: str):
#     """Remove a permission from an entry."""
#
#     operation = (
#         self.client()
#         .permissions()
#         .delete(
#             fileId=entry_id,
#             permissionId=permission_id,
#         )
#     )
#
#     self.cache_remove(entry_id)
#     return operation
#
# def file_rename(self, entry_id: str, new_name: typing.Optional[str] = None):
#     """Rename an entry."""
#
#     if not new_name:
#         logger.warning(f"No new names given for file id '{entry_id}'.")
#         return None
#
#     # name: string - The name of the file.
#     # This is not necessarily unique within a folder.
#     # Note that for immutable items such as the top level folders of shared drives,
#     # My Drive root folder, and Application Data folder the name is constant.- writable
#
#     # NOTE: Tried to update originalFilename, but that does not seem to be saved.
#     #       The old originalFilename is always returned after updating.
#
#     # originalFilename: string - The original filename of the uploaded content if available,
#     # or else the original value of the name field. This is only available for files with
#     # binary content in Google Drive. - writable
#
#     body = {}
#     if new_name:
#         body["name"] = new_name
#
#     operation = (
#         self.client()
#         .files()
#         .update(
#             fileId=entry_id,
#             body=body,
#             fields=self._entry_fields,
#         )
#     )
#
#     self.cache_remove(entry_id)
#     return operation
#
# def permission_transfer(
#     self,
#     file_id: str,
#     permission_id: typing.Optional[str],
#     new_type: str,
#     new_owner: str,
#     new_parent_id: str,
# ):
#     # NOTE: Ownership transfer from a personal to a business account is possible!
#     # NOTE: This bug does not seem to be related: https://issuetracker.google.com/issues/228791253
#
#     fields = ",".join(["id"])
#     service = self.client()
#
#     # build the new permission
#     if permission_id and new_type == self.type_domain:
#         # transfer to a business account where the new owner already has a permission
#         operation = service.permissions().update(
#             fileId=file_id,
#             body={
#                 "type": self.type_domain,
#                 "role": "owner",
#                 "domain": new_owner,
#                 "parents": [new_parent_id],
#             },
#             transferOwnership=True,
#             fields=fields,
#         )
#
#     elif not permission_id and new_type == self.type_domain:
#         # transfer to a business account where the new owner does not have a permission
#         operation = service.permissions().create(
#             fileId=file_id,
#             body={
#                 "type": self.type_domain,
#                 "role": "owner",
#                 "domain": new_owner,
#                 "parents": [new_parent_id],
#             },
#             transferOwnership=True,
#             fields=fields,
#         )
#
#     elif permission_id and new_type == self.type_user:
#         # transfer to a personal account where the new owner already has a permission
#         operation = service.permissions().update(
#             fileId=file_id,
#             body={
#                 "type": self.type_user,
#                 "role": "owner",
#                 "emailAddress": new_owner,
#                 "pendingOwner": True,
#                 "parents": [new_parent_id],
#             },
#             transferOwnership=True,
#             fields=fields,
#         )
#
#     elif not permission_id and new_type == self.type_user:
#         # transfer to a personal account where the new owner does not have a permission
#         operation = service.permissions().create(
#             fileId=file_id,
#             body={
#                 "type": self.type_user,
#                 "role": "owner",
#                 "emailAddress": new_owner,
#                 "pendingOwner": True,
#                 "parents": [new_parent_id],
#             },
#             transferOwnership=True,
#             fields=fields,
#         )
#
#     else:
#         raise ValueError(
#             "Unknown combination for "
#             f"permission id '{permission_id}' type '{new_type}'."
#         )
#
#     self.cache_remove(file_id)
#     return operation
#
# def create_folder(
#     self,
#     entry: models.GoogleDriveEntry,
#     parent_id: str,
#     body_params: dict,
#     **kwargs,
# ):
#     """
#     Create a new folder with the same name as entry (which much be a folder).
#     Add a custom property to the copy and the original.
#     Include as much metadata as possible.
#     """
#
#     if not entry.is_dir:
#         raise ValueError(f"Cannot create folder for {str(entry)}.")
#
#     name = entry.name
#
#     operation = (
#         self.client()
#         .files()
#         .create(
#             **kwargs,
#             body={
#                 **body_params,
#                 "createdTime": entry.date_created,
#                 "modifiedTime": entry.date_modified,
#                 "name": name,
#                 "parents": [parent_id],
#                 "mimeType": models.GoogleDriveEntry.mime_type_dir(),
#             },
#             fields=self._entry_fields,
#         )
#     )
#     return operation
#
# def copy_file(
#     self,
#     entry: models.GoogleDriveEntry,
#     parent: models.GoogleDriveEntry,
#     custom_properties: dict,
# ):
#     """Copy a file that is not owned to the same folder, with the same name."""
#
#     if entry.is_dir:
#         raise ValueError(f"Cannot copy {str(entry)}.")
#
#     name = entry.name
#
#     operation = (
#         self.client()
#         .files()
#         .copy(
#             fileId=entry.entry_id,
#             body={
#                 "createdTime": entry.date_created,
#                 "modifiedTime": entry.date_modified,
#                 "description": entry.description,
#                 "name": name,
#                 "parents": [parent.entry_id],
#                 "properties": custom_properties,
#                 "mimeType": entry.mime_type,
#             },
#             fields=self._entry_fields,
#         )
#     )
#     return operation
#
# def update_entry(self, entry: models.GoogleDriveEntry, **kwargs):
#     """Update any aspect of an entry."""
#
#     operation = (
#         self.client()
#         .files()
#         .update(
#             **kwargs,
#             fileId=entry.entry_id,
#             fields=self._entry_fields,
#         )
#     )
#     self.cache_remove(entry.entry_id)
#     return operation
#
