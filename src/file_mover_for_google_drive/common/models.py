"""The data models."""
import abc
import dataclasses
import enum
import json
import logging
import pathlib
import typing
from datetime import datetime

logger = logging.getLogger(__name__)


class GoogleDrivePropertyKeyOptions(enum.Enum):
    CUSTOM_COPY_FILE_ID = "CustomFileMoverCopyFileId"
    """Applied to an unowned entry to track the copy.

    Used to keep track of which files and folders were copied to create owned
    copies within the same account.

    The key name for a custom property put on an original (not owned) entry,
    which contains the file id of the copied entry.
    """

    CUSTOM_ORIGINAL_FILE_ID = "CustomFileMoverOriginalFileId"
    """Applied to an owned entry to track the original.

    Used to keep track of which files and folders were copied to create owned
    copies within the same account.

    The key name for a custom property put on a copied (owned) entry,
    which contains the file id of the original entry.
    """


class GoogleDriveAccountTypeOptions(enum.Enum):
    """The Google Drive account type. Dictates the features available."""

    PERSONAL = "personal"
    """A personal account that does not contain shared drives.
    May have access to shared drives."""
    BUSINESS = "business"
    """A business account that does contain shared drives."""


class GoogleDrivePermissionRoleOptions(enum.Enum):
    """The options for 'role' in the Google Drive API.

    Ref: https://developers.google.com/drive/api/guides/ref-roles
    """

    OWNER = "owner"
    EDITOR = "writer"
    COMMENTER = "commenter"
    VIEWER = "reader"
    ORGANIZER = "organizer"
    FILE_ORGANIZER = "fileOrganizer"


class GoogleDrivePermissionTypeOptions(enum.Enum):
    """Google Drive permission type options."""

    USER = "user"
    """requires prop 'emailAddress' to be set"""
    GROUP = "group"
    """requires prop 'emailAddress' to be set"""
    DOMAIN = "domain"
    """requires prop 'domain' to be set"""
    ANYONE = "anyone"


class PlanReportActions(enum.Enum):
    """Plan report item action options."""

    CREATE_FOLDER = "create-folder"
    RENAME_FILE = "rename-file"
    DELETE_PERMISSION = "delete-permission"
    COPY_FILE = "copy-file"
    MOVE_ENTRY = "move-entry"


class PlanReportOutcomes(enum.Enum):
    """Plan report item outcome options."""

    UNKNOWN = "unknown"
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclasses.dataclass(frozen=True)
class BaseModel(abc.ABC):
    """Base model abstract class."""

    @classmethod
    def load_data(cls, data: typing.Mapping) -> "BaseModel":
        """Load model data from a mapping.

        Args:
            data: The raw dictionary.

        Returns:
            A new instance of this config class.
        """
        raise NotImplementedError()

    def save_data(self) -> typing.Mapping:
        """Save model data to a mapping.

        Returns:
            The data from this config class as a dictionary.
        """
        raise NotImplementedError()


TypeBaseModel_co = typing.TypeVar("TypeBaseModel_co", bound="BaseModel", covariant=True)


@dataclasses.dataclass(frozen=True)
class ConfigAuth(BaseModel):
    """The authentication configuration."""

    credentials_file: pathlib.Path
    """The app credentials file."""
    token_file: pathlib.Path
    """The authorised access token file."""

    @classmethod
    def load_data(cls, data: typing.Mapping) -> "ConfigAuth":
        credentials_file = data.get("credentials_file")
        if not credentials_file:
            raise ValueError("Must provide credentials file path.")

        token_file = data.get("token_file")
        if not token_file:
            raise ValueError("Must provide token file path.")

        result = ConfigAuth(
            credentials_file=pathlib.Path(credentials_file),
            token_file=pathlib.Path(token_file),
        )

        if not result.credentials_file.exists():
            raise ValueError(
                f"The credentials file '{result.credentials_file}' "
                "must be available, but does not exist ."
            )
        return result

    def save_data(self) -> typing.Mapping:
        return {
            "credentials_file": str(self.credentials_file.absolute()),
            "token_file": str(self.token_file.absolute()),
        }


@dataclasses.dataclass(frozen=True)
class ConfigReports(BaseModel):
    """The report files configuration."""

    entries_dir: pathlib.Path
    """Contains csv files where each row is a file or folder."""
    permissions_dir: pathlib.Path
    """Contains csv files where each row is a permission."""
    plans_dir: pathlib.Path
    """Contains csv files where each row is a planned change."""
    outcomes_dir: pathlib.Path
    """Contains csv files where each row is the result of attempting a change."""

    @classmethod
    def load_data(cls, data: typing.Mapping) -> "ConfigReports":
        items = ["entries_dir", "permissions_dir", "plans_dir", "outcomes_dir"]

        params = {}
        for item in items:
            value = data.get(item)
            if not value:
                raise ValueError(f"Must provide {item}.")
            path = pathlib.Path(value)
            if not path.exists():
                path.mkdir(exist_ok=True, parents=True)
            params[item] = path

        result = ConfigReports(**params)

        return result

    def save_data(self) -> typing.Mapping:
        return {
            "entries_dir": str(self.entries_dir.absolute()),
            "permissions_dir": str(self.permissions_dir.absolute()),
            "plans_dir": str(self.plans_dir.absolute()),
            "outcomes_dir": str(self.outcomes_dir.absolute()),
        }


@dataclasses.dataclass(frozen=True)
class ConfigActions(BaseModel):
    """The action configuration."""

    permissions_delete_other_users: bool
    """Whether to delete permissions granted to other non-owner users."""
    permissions_delete_link: bool
    """Whether to delete the 'Anyone with Link' permission."""
    entry_name_delete_prefix_copy_of: bool
    """Whether to remove the 'Copy of ' file name prefix."""
    create_owned_file_copy: bool
    """Whether to create a copy of files that are not owned."""
    create_owned_folder_and_move_contents: bool
    """Whether to create a folder to hold the contents of an unowned folder."""

    @classmethod
    def load_data(cls, data: typing.Mapping) -> "ConfigActions":
        items = [
            "permissions_delete_other_users",
            "permissions_delete_link",
            "entry_name_delete_prefix_copy_of",
            "create_owned_file_copy",
            "create_owned_folder_and_move_contents",
        ]
        params = {}
        for item in items:
            value = data.get(item, False)
            if value is True or value == "true" or value == "True":
                params[item] = True
            else:
                params[item] = False

        return ConfigActions(**params)

    def save_data(self) -> typing.Mapping:
        items = [
            "permissions_delete_other_users",
            "permissions_delete_link",
            "entry_name_delete_prefix_copy_of",
            "create_owned_file_copy",
            "create_owned_folder_and_move_contents",
        ]
        result = {}
        for item in items:
            result[item] = getattr(self, item)
        return result


@dataclasses.dataclass(frozen=True)
class ConfigAccount(BaseModel):
    """The account configuration."""

    account_type: GoogleDriveAccountTypeOptions
    """The type of account.
    One of 'personal', 'business'."""
    drive_id: str
    """The drive id.
    'My Drive' for personal accounts.
    The Shared Drive id for business accounts."""
    account_id: str
    """The account identifier.
    The email address for personal accounts.
    The domain name for business accounts."""
    top_folder_id: str
    """The id of the top-level (starting) folder."""

    @classmethod
    def drive_name_my_drive(cls):
        """The name of the only available drive for personal accounts.

        Returns:
            The drive name for personal accounts 'My Drive'.
        """
        return "My Drive"

    @classmethod
    def load_data(cls, data: typing.Mapping) -> "ConfigAccount":
        params: typing.Mapping[
            str, typing.Union[str, GoogleDriveAccountTypeOptions]
        ] = {
            **data,
            "account_type": GoogleDriveAccountTypeOptions(data.get("account_type")),
        }

        if params.get("account_type") == GoogleDriveAccountTypeOptions.PERSONAL:
            expected_name = cls.drive_name_my_drive()
            if params.get("drive_id") != expected_name:
                raise ValueError(
                    f"The drive name for personal accounts must be '{expected_name}'."
                )

        return ConfigAccount(**params)

    def save_data(self) -> typing.Mapping:
        return {
            "account_type": self.account_type.value,
            "drive_id": self.drive_id,
            "account_id": self.account_id,
            "top_folder_id": self.top_folder_id,
        }


@dataclasses.dataclass(frozen=True)
class ConfigProgram(BaseModel):
    """The program configuration."""

    auth: ConfigAuth
    """The authentication config."""
    reports: ConfigReports
    """The reports config."""
    actions: ConfigActions
    """The actions config."""
    account: ConfigAccount
    """The account config."""

    @property
    def num_retries(self) -> int:
        """The number of times to attempt a remote communication.

        Returns:
            The number of attempts.
        """
        return 3

    @classmethod
    def load_data(cls, data: typing.Mapping) -> "ConfigProgram":
        items: typing.Mapping[str, TypeBaseModel_co] = {
            "auth": ConfigAuth,
            "reports": ConfigReports,
            "actions": ConfigActions,
            "account": ConfigAccount,
        }

        params = {}
        for k, v in items.items():
            raw = data.get(k, {})
            params[k] = v.load_data(raw)

        return ConfigProgram(**params)

    def save_data(self) -> typing.Mapping:
        return {
            "auth": self.auth.save_data(),
            "reports": self.reports.save_data(),
            "actions": self.actions.save_data(),
            "account": self.account.save_data(),
        }

    @classmethod
    def load_file(cls, path: pathlib.Path) -> "ConfigProgram":
        """Load the config data from a file.

        Args:
            path: The file path.

        Returns:
            The program config data.
        """
        with open(path, "rt", encoding="utf-8") as handle:
            raw = json.load(handle)
            return cls.load_data(raw)

    def save_file(self, path: pathlib.Path) -> None:
        """Save the config data to a file.

        Args:
            path: The file path.

        Returns:
            None
        """
        with open(path, "wt", encoding="utf-8") as file_handle:
            json.dump(self.save_data(), file_handle)


@dataclasses.dataclass(frozen=True, order=True)
class GoogleDrivePermission(BaseModel):
    """A Google Drive permission that specifies access to an entry."""

    entry_type: GoogleDrivePermissionTypeOptions
    """The type of permission.
    For user or group, you must provide an emailAddress.
    For domain, you must provide a domain.
    For anyone, there are no extra requirements.
    """
    role: GoogleDrivePermissionRoleOptions
    """The role option."""
    entry_id: str
    """The identifier for the permission. 
    e.g. '11823143700967846661', 'anyoneWithLink'
    """
    user_email: typing.Optional[str] = None
    """The email address of the user or group to which this permission refers."""
    domain: typing.Optional[str] = None
    """The domain to which this permission refers.

    - The entire domain, such as "your-company.com."
    - A target audience, such as "ID.audience.googledomains.com."
    """
    display_name: typing.Optional[str] = None
    """The "pretty" name of the value of the permission.
        The following is a list of examples for each type of permission:

        - user - User's full name.
        - group - Name of the Google Group, such as 'The Company Administrators'
        - domain - String domain name, such as 'your-company.com'
        - anyone - No displayName is present.

        Returns:
            The display name.
        """

    @classmethod
    def load_data(cls, data: typing.Mapping) -> "GoogleDrivePermission":
        params = {}

        entry_id = data.get("id")
        if not entry_id or not entry_id.strip():
            raise ValueError("Permission must include 'id'.")
        params["entry_id"] = entry_id

        entry_type = data.get("type")
        if not entry_type:
            raise ValueError("Permission must include 'type'.")
        entry_type = GoogleDrivePermissionTypeOptions(entry_type)
        params["entry_type"] = entry_type

        role = data.get("role")
        if not role:
            raise ValueError("Permission must include 'role'.")
        params["role"] = GoogleDrivePermissionRoleOptions(role)

        if entry_type in [
            GoogleDrivePermissionTypeOptions.USER,
            GoogleDrivePermissionTypeOptions.GROUP,
        ]:
            params["user_email"] = data.get("emailAddress")

        display_name = data.get("displayName")
        if display_name:
            params["display_name"] = str(display_name)

        if entry_type == GoogleDrivePermissionTypeOptions.DOMAIN:
            params["domain"] = data.get("domain")

        result = GoogleDrivePermission(**params)

        if not result.entry_type:
            raise ValueError("Entry type is not set.")
        if not result.role:
            raise ValueError("Role is not set.")
        if not result.entry_id:
            raise ValueError("Entry id is not set.")
        if (
            not result.display_name
            and result.entry_type != GoogleDrivePermissionTypeOptions.ANYONE
        ):
            raise ValueError("Display name is not set.")
        if not result.user_email and result.entry_type in [
            GoogleDrivePermissionTypeOptions.USER,
            GoogleDrivePermissionTypeOptions.GROUP,
        ]:
            raise ValueError("User email must be set for type 'user' or 'group'.")
        if not result.domain and result.entry_type in [
            GoogleDrivePermissionTypeOptions.DOMAIN,
        ]:
            raise ValueError("Domain must be set for type 'domain'.")

        return result

    def save_data(self) -> typing.Mapping:
        raise NotImplementedError("Cannot save permission data.")

    @classmethod
    def get_display_name(
        cls, permission: typing.Optional["GoogleDrivePermission"]
    ) -> str:
        if permission and permission.display_name:
            return permission.display_name
        return "Unknown user name"

    def __str__(self) -> str:
        entry_type = self.entry_type
        role = self.role
        name = self.display_name
        email = self.user_email
        if entry_type == GoogleDrivePermissionTypeOptions.USER:
            return f"{name} <{email}> ({role.name})"

        if entry_type == GoogleDrivePermissionTypeOptions.GROUP:
            return f"{name} <{email}> ({role.name})"

        if entry_type == GoogleDrivePermissionTypeOptions.DOMAIN:
            return f"{name} ({role.name})"

        if entry_type == GoogleDrivePermissionTypeOptions.ANYONE:
            return f"anyone with link ({role.name})"

        raise ValueError(f"Unknown type '{entry_type}'.")

    def __repr__(self) -> str:
        return str(self)


@dataclasses.dataclass(frozen=True, order=True)
class GoogleDriveEntry(BaseModel):
    """A Google Drive file or folder."""

    name: str
    """The name of the file or folder. There may be duplicates."""
    mime_type: str
    """The mime / media type of the file or folder."""
    description: str
    """A short description of the file."""
    date_created: datetime
    """The time at which the file was created."""
    date_modified: datetime
    """The last time anyone modified the file."""
    entry_id: str
    """The identifier of the file or folder."""
    parent_id: str
    """The identifier of the folder that contains this file or folder."""
    size_bytes: int
    """
    The size of the file's content in bytes.
    This field is populated for files with binary content
    stored in Google Drive and for Docs Editors files;
    it is not populated for shortcuts or folders.
    """
    quota_bytes: int
    """
    The number of storage quota bytes used by the file.
    This includes the head revision as well as
    previous revisions with keepForever enabled.
    """
    properties_shared: typing.Mapping
    """A collection of arbitrary key-value pairs that are visible to all apps."""
    properties_app: typing.Mapping
    """A collection of arbitrary key-value pairs 
    that are private to the requesting app."""
    permissions_all: list[GoogleDrivePermission]
    """A list of permissions, normalised for both personal and business accounts."""
    account: ConfigAccount
    """The account that contains this file or folder."""
    view_link: typing.Optional[str] = None
    """A link for opening the file in an editor or viewer in a browser."""
    checksum_sha256: typing.Optional[str] = None
    name_original: typing.Optional[str] = None
    """The original filename of the uploaded content if available, 
    or else the original value of the name field. 
    This is only available for files with binary content in Google Drive."""

    @property
    def is_dir(self) -> bool:
        """Whether this entry is a folder or not.

        Returns:
            True if this entry is a folder.
        """
        return self.mime_type == GoogleDriveEntry.mime_type_dir()

    @property
    def is_copy(self) -> bool:
        prop_key = GoogleDrivePropertyKeyOptions.CUSTOM_ORIGINAL_FILE_ID.value
        prop_value = self.custom_property(prop_key)
        return prop_value and len(prop_value) > 0

    @property
    def is_original(self) -> bool:
        prop_key = GoogleDrivePropertyKeyOptions.CUSTOM_COPY_FILE_ID.value
        prop_value = self.custom_property(prop_key)
        return prop_value and len(prop_value) > 0

    @property
    def entry_type(self) -> str:
        """The type of entry: either 'file' or 'folder'.

        Returns:
            The type of entry.
        """
        return "folder" if self.is_dir else "file"

    @classmethod
    def load_data(cls, data: typing.Mapping) -> "GoogleDriveEntry":
        if "fileMoverExtraAccount" not in data:
            raise ValueError("Must include the account information.")
        if "fileMoverExtraPermissions" not in data:
            raise ValueError("Must include the response from permissions.list.")

        included_permissions = [
            GoogleDrivePermission.load_data(i) for i in data.get("permissions", [])
        ]

        params = {
            "permissions_all": included_permissions,
            "account": data.get("fileMoverExtraAccount"),
        }

        entry_id = data.get("id")
        if not entry_id or not entry_id.strip():
            raise ValueError("Entry must include 'id'.")
        params["entry_id"] = entry_id

        ids: list[str] = data.get("parents", [])
        if len(ids) != 1:
            raise ValueError(f"Unexpected value for 'parents': '{ids}'.")
        params["parent_id"] = ids[0]

        date_created = data.get("createdTime")
        if date_created:
            params["date_created"] = datetime.fromisoformat(date_created)

        date_modified = data.get("modifiedTime")
        if date_modified:
            params["date_modified"] = datetime.fromisoformat(date_modified)

        params["name"] = data.get("name")
        params["description"] = data.get("description")
        params["mime_type"] = data.get("mimeType")
        params["view_link"] = data.get("webViewLink")
        params["size_bytes"] = int(str(data.get("size", "0")))
        params["quota_bytes"] = int(str(data.get("quotaBytesUsed", "0")))
        params["checksum_sha256"] = data.get("sha256Checksum")
        params["name_original"] = data.get("originalFilename")
        params["properties_shared"] = data.get("properties", {})
        params["properties_app"] = data.get("appProperties", {})

        # drive_id = data.get("driveId")
        # """ID of the shared drive the file resides in.
        # Only populated for items in shared drives."""

        permission_ids = data.get("permissionIds")
        # """List of permission IDs for users with access to this file."""

        has_augmented_permissions = data.get("hasAugmentedPermissions")
        # """Whether there are permissions directly on this file.
        # This field is only populated for items in shared drives."""

        permissions_list = data["fileMoverExtraPermissions"]

        if included_permissions != permissions_list:
            raise ValueError([included_permissions, permissions_list])
        if permission_ids != [i.entry_id for i in included_permissions]:
            raise ValueError([included_permissions, permission_ids])
        if permission_ids != [i.entry_id for i in permissions_list]:
            raise ValueError([permissions_list, permission_ids])

        if has_augmented_permissions:
            raise ValueError(data)

        return GoogleDriveEntry(**params)

    def save_data(self) -> typing.Mapping:
        raise NotImplementedError("Cannot save entry data.")

    @property
    def permission_owner_user(self) -> GoogleDrivePermission:
        """Get the permission for the owner of this entry.

        Returns:
            The owner permission, if available.
        """
        role_owner = GoogleDrivePermissionRoleOptions.OWNER
        perm_type_user = GoogleDrivePermissionTypeOptions.USER
        owners = []
        for permission in self.permissions_all:
            if permission.role != role_owner:
                continue
            if permission.entry_type != perm_type_user:
                continue
            owners.append(permission)

        if len(owners) < 1:
            raise ValueError(
                f"Found no owner for {str(self)} " f"with {self.str_permissions}."
            )

        if len(owners) == 1:
            return owners[0]

        raise ValueError(
            f"Found more than one owner for {str(self)} "
            f"with {self.str_permissions}."
        )

    def get_permission_by_email(
        self, email: str
    ) -> typing.Optional[GoogleDrivePermission]:
        """Get the permission for the given email address.

        Args:
            email: The email address to search for.

        Returns:
            The matching permission, if available.
        """
        for permission in self.permissions_all:
            if permission.user_email == email:
                return permission
        return None

    @property
    def str_permissions(self) -> str:
        """Get a string representation of this entry's permissions.

        Returns:
            A string representation of this entry's permissions.
        """
        count = len(self.permissions_all)
        display = "; ".join(sorted(str(p) for p in self.permissions_all))
        return f"{count} permissions [{display}]"

    @classmethod
    def mime_type_dir(cls) -> str:
        """Get the Google Drive mime type for a folder.

        Returns:
            Folder mime type.
        """
        return "application/vnd.google-apps.folder"

    @classmethod
    def required_properties(cls) -> str:
        """Get the properties required from the API to correctly populate an entry
        instance.

        Returns:
            A list of API fields.
        """
        return ",".join(
            [
                "id",
                "name",
                "originalFilename",
                "mimeType",
                "parents",
                "permissions",
                "permissionIds",
                "webViewLink",
                "sha256Checksum",
                "size",
                "quotaBytesUsed",
                "properties",
                "description",
                "createdTime",
                "modifiedTime",
                "hasAugmentedPermissions",
            ]
        )

    @classmethod
    def build_path_str(cls, entry_path: list["GoogleDriveEntry"]) -> str:
        """Build the folder path hierarchy as a path string.

        Args:
            entry_path: The list of ancestor entries.

        Returns:
            The folder path string.
        """
        return "/".join([entry.name for entry in entry_path if entry.name])

    def custom_property(self, key: str) -> typing.Optional[typing.Any]:
        """Get the value for a property key.

        Args:
            key: The property key.

        Returns:
            The property value or None.
        """
        return self.properties_shared.get(key, None)

    def is_owned_by(self, email: str) -> bool:
        """Check if this entry is owned by the user with the given email.

        Args:
            email: The user email address.

        Returns:
            True if the user with the given email address owns this entry.
        """
        permission_owner_user = self.permission_owner_user
        if not permission_owner_user:
            raise ValueError()
        return permission_owner_user.user_email == email

    def __str__(self) -> str:
        entry_type = self.entry_type
        props = ";".join([f"{k}={v}" for k, v in self.properties_shared.items()])
        return f"{entry_type} '{self.name}' (id {self.entry_id}) props '{props}'"

    def __repr__(self) -> str:
        return str(self)
