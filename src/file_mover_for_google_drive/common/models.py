import dataclasses
import json
import logging
import pathlib
import typing

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Config:
    auth_credentials_file: pathlib.Path
    auth_token_file: pathlib.Path

    report_entries_dir: pathlib.Path
    report_permissions_dir: pathlib.Path
    report_plans_dir: pathlib.Path
    report_outcomes_dir: pathlib.Path

    action_remove_prefix_copy_of: bool
    action_permissions_remove_users: bool
    action_permissions_remove_anyone: bool
    action_copy_unowned: bool
    action_move_to_owned_folder: bool
    action_transfer_ownership: bool

    personal_account_top_folder_id: str
    personal_account_email: str

    business_account_top_folder_id: str
    business_account_shared_drive: str
    business_account_domain: str

    num_retries: int = 3

    @property
    def custom_prop_original_key(self):
        """The key name for a custom property put on a copied (owned) entry,
        which contains the file id of the original entry."""
        return "CustomOriginalFileId"

    @property
    def custom_prop_copy_key(self):
        """
        The key name for a custom property put on an original (not owned) entry,
        which contains the file id of the copied entry.
        """
        return "CustomCopyFileId"

    @property
    def custom_prop_prev_account_key(self):
        """
        The key name for a custom property put on an owned entry,
        which contains the account id of the previous account
        that contained this file before the ownership transfer.
        """
        return "CustomPreviousAccountId"

    @property
    def custom_prop_new_account_key(self):
        """The key name for a custom property put on a not-owned entry,
        which contains the account id of the account
        that now contains the copied (owned) file."""
        return "CustomNewAccountId"

    def validate(self) -> bool:
        is_valid: typing.Optional[bool] = None

        check_items = {
            "credentials file": self.auth_credentials_file,
            "token file": self.auth_token_file,
            "entries file": self.report_entries_dir,
            "permissions file": self.report_permissions_dir,
            "plans file": self.report_plans_dir,
            "outcomes file": self.report_outcomes_dir,
            "personal_account_top_folder_id": self.personal_account_top_folder_id,
            "personal_account_email": self.personal_account_email,
            "business_account_top_folder_id": self.business_account_top_folder_id,
            "business_account_shared_drive": self.business_account_shared_drive,
            "business_account_domain": self.business_account_domain,
        }

        if self.auth_credentials_file and not self.auth_credentials_file.exists():
            logger.error(
                "The credentials file must be available, but does not exist '%s'.",
                self.auth_credentials_file,
            )
            is_valid = False

        for name, check in check_items.items():
            if not check:
                logger.error("The %s must be set, but was not.", name)
                is_valid = False

        return True if is_valid is None else False

    @classmethod
    def load(cls, path: pathlib.Path) -> "Config":
        with open(path, "rt") as f:
            raw = json.load(f)
            config = Config(
                auth_credentials_file=pathlib.Path(raw.get("auth_credentials_file")),
                auth_token_file=pathlib.Path(raw.get("auth_token_file")),
                report_entries_dir=pathlib.Path(raw.get("report_entries_dir")),
                report_permissions_dir=pathlib.Path(raw.get("report_permissions_dir")),
                report_plans_dir=pathlib.Path(raw.get("report_plans_dir")),
                report_outcomes_dir=pathlib.Path(raw.get("report_outcomes_dir")),
                action_remove_prefix_copy_of=raw.get(
                    "action_personal_account_file_names_remove_prefix_copy_of"
                ),
                action_permissions_remove_users=raw.get(
                    "action_personal_account_permissions_remove_if_not_owner_and_not_current_user"
                ),
                action_permissions_remove_anyone=raw.get(
                    "action_personal_account_permissions_remove_access_for_anyone_with_link"
                ),
                action_copy_unowned=raw.get(
                    "action_personal_account_copy_unowned_files_and_folders"
                ),
                action_move_to_owned_folder=raw.get(
                    "action_personal_account_move_files_and_folders_from_unowned_folder_to_owned_folder"
                ),
                action_transfer_ownership=raw.get(
                    "action_transfer_ownership_from_personal_account_to_business_account"
                ),
                personal_account_top_folder_id=raw.get(
                    "personal_account_top_folder_id"
                ),
                personal_account_email=raw.get("personal_account_email"),
                business_account_top_folder_id=raw.get(
                    "business_account_top_folder_id"
                ),
                business_account_shared_drive=raw.get("business_account_shared_drive"),
                business_account_domain=raw.get("business_account_domain"),
            )

            if config.validate():
                return config
            else:
                raise ValueError(f"Config file is not valid '{path}'.")

    def save(self, path: pathlib.Path) -> None:
        data = {
            "auth_credentials_file": str(self.auth_credentials_file),
            "auth_token_file": str(self.auth_token_file),
            "report_entries_dir": str(self.report_entries_dir),
            "report_permissions_dir": str(self.report_permissions_dir),
            "report_plans_dir": str(self.report_plans_dir),
            "report_outcomes_dir": str(self.report_outcomes_dir),
            "action_personal_account_file_names_remove_prefix_copy_of": self.action_remove_prefix_copy_of,
            "action_personal_account_permissions_remove_if_not_owner_and_not_current_user": self.action_permissions_remove_users,
            "action_personal_account_copy_unowned_files_and_folders": self.action_copy_unowned,
            "action_personal_account_permissions_remove_access_for_anyone_with_link": self.action_permissions_remove_anyone,
            "action_personal_account_move_files_and_folders_from_unowned_folder_to_owned_folder": self.action_move_to_owned_folder,
            "action_transfer_ownership_from_personal_account_to_business_account": self.action_transfer_ownership,
            "personal_account_top_folder_id": self.personal_account_top_folder_id,
            "personal_account_email": self.personal_account_email,
            "business_account_top_folder_id": self.business_account_top_folder_id,
            "business_account_shared_drive": self.business_account_shared_drive,
            "business_account_domain": self.business_account_domain,
            "num_retries": self.num_retries,
        }
        with open(path, "wt") as f:
            json.dump(data, f)


class GoogleDrivePermission:
    def __init__(self, entry: dict):
        self._raw = entry

    @property
    def entry_id(self):
        # e.g. '11823143700967846661', 'anyoneWithLink'
        return self._raw.get("id")

    @property
    def entry_type(self):
        # e.g. 'user', 'anyone'
        return self._raw.get("type")

    @property
    def user_email(self):
        return self._raw.get("emailAddress") if self.entry_type == "user" else None

    @property
    def user_name(self):
        return self._raw.get("displayName") if self.entry_type == "user" else None

    @property
    def domain(self):
        return self._raw.get("domain") if self.entry_type == "domain" else None

    @property
    def role(self):
        # e.g. 'writer', 'owner'
        return self._raw.get("role")

    @classmethod
    def get_display(
        cls,
        perm_type: str,
        role: str,
        name: typing.Optional[str] = None,
        email: typing.Optional[str] = None,
    ):
        if perm_type == "user":
            return f"{name} <{email}> ({role})"
        elif perm_type == "anyone":
            return f"AnyoneWithLink ({role})"
        else:
            raise ValueError(f"Unknown type '{perm_type}'.")

    def __str__(self):
        return self.get_display(
            self.entry_type, self.role, self.user_name, self.user_email
        )

    def __repr__(self) -> str:
        return str(self)


class GoogleDriveEntry:
    def __init__(
        self,
        entry: dict,
        collection_type: str,
        collection_name: str,
        collection_id: str,
    ):
        self._raw = entry
        self._collection_type = collection_type
        self._collection_name = collection_name
        self._collection_id = collection_id

        self._shared_drive_permissions: list[GoogleDrivePermission] = []

    @property
    def entry_id(self):
        return self._raw.get("id")

    @property
    def view_link(self):
        return self._raw.get("webViewLink")

    @property
    def name(self):
        return self._raw.get("name")

    @property
    def description(self):
        return self._raw.get("description")

    @property
    def mime_type(self):
        return self._raw.get("mimeType")

    @property
    def name_original(self):
        return self._raw.get("originalFilename")

    @property
    def is_dir(self):
        return self.mime_type == GoogleDriveEntry.mime_type_dir()

    @property
    def entry_type(self):
        return "folder" if self.is_dir else "file"

    @property
    def parent_id(self):
        ids = self._raw.get("parents", [])
        if len(ids) == 1:
            return ids[0]
        raise ValueError(f"Unexpected value for 'parents': '{ids}'.")

    @property
    def permissions(self):
        my_drive = [GoogleDrivePermission(i) for i in self._raw.get("permissions", [])]
        shared_drive = self._shared_drive_permissions
        return [*my_drive, *shared_drive]

    @property
    def permission_owner_user(self):
        owners = []
        for p in self.permissions:
            if p.role != "owner":
                continue
            if p.entry_type != "user":
                continue
            owners.append(p)
        if len(owners) < 1:
            raise ValueError(
                f"Found no owner for {str(self)} with {self.str_permissions}."
            )
        elif len(owners) == 1:
            return owners[0]
        else:
            raise ValueError(
                f"Found more than one owner for {str(self)} with {self.str_permissions}."
            )

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
    def permissions_str(self):
        return "; ".join(sorted(str(p) for p in self.permissions))

    @property
    def checksum_sha256(self):
        return self._raw.get("sha256Checksum")

    @property
    def size_bytes(self):
        """
        The size of the file's content in bytes.
        This field is populated for files with binary content stored in Google Drive and for Docs Editors files;
        it is not populated for shortcuts or folders.
        """
        return self._raw.get("size", 0)

    @property
    def quota_bytes(self):
        """
        The number of storage quota bytes used by the file.
        This includes the head revision as well as previous revisions with keepForever enabled.
        """
        return self._raw.get("quotaBytesUsed", 0)

    @property
    def custom_properties(self):
        return self._raw.get("properties", {})

    @property
    def date_created(self):
        return self._raw.get("createdTime")

    @property
    def date_modified(self):
        return self._raw.get("modifiedTime")

    @property
    def str_permissions(self):
        permissions = self.permissions_str
        return f"{len(self.permissions)} permissions [{permissions}]"

    @property
    def has_augmented_permissions(self):
        return self._raw.get("hasAugmentedPermissions", False)

    @property
    def get_raw(self):
        return self._raw

    @classmethod
    def mime_type_dir(cls):
        return "application/vnd.google-apps.folder"

    @classmethod
    def required_properties(cls) -> str:
        return ",".join(
            [
                "id",
                "name",
                "originalFilename",
                "mimeType",
                "parents",
                "permissions",
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
        return "/".join([entry.name for entry in entry_path])

    def custom_property(self, key):
        return self._raw.get("properties", {}).get(key, None)

    def is_owned_by(self, email: str):
        permission_owner_user = self.permission_owner_user
        if not permission_owner_user:
            raise ValueError()
        return permission_owner_user.user_email == email

    def set_shared_drive_permissions(self, items: list[GoogleDrivePermission]):
        self._shared_drive_permissions = items

    def __str__(self) -> str:
        entry_type = self.entry_type
        return f"{entry_type} '{self.name}' (id {self.entry_id})"

    def __repr__(self) -> str:
        return str(self)
