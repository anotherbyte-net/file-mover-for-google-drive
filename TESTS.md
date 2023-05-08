# Testing File Mover for Google Drive

Tests are written using the `googleapiclient.http` mocks.

The data used is:

```yaml
entries:
  - name: "Folder Top"
    id: "personal-folder-level0"
    parent_id: "personal-folder-level0-parent"
    permissions:
      - "personal-permission-current-user": "owner"

  - name: "Entry Level 1 - Folder 1"
    id: "personal-folder-level1-001"
    parent_id: "personal-folder-level0"
    permissions:
      - "personal-permission-current-user": "owner"

  - name: "Entry Level 1 - File 1.pdf"
    id: "personal-file-level1-001"
    parent_id: "personal-folder-level0"
    permissions:
      - "personal-permission-current-user": "owner"

  - name: "Entry Level 2 - Folder 1"
    id: "personal-folder-level2-001"
    parent_id: "personal-folder-level1-001"
    permissions:
      - "personal-permission-current-user": "writer"
      - "personal-other-user-1": "owner"

  - name: "Entry Level 2 - Folder 1"
    id: "personal-folder-level2-002"
    parent_id: "personal-folder-level1-001"
    permissions:
      - "personal-permission-current-user": "owner"
    notes:
      - "This is the pair for personal-folder-level2-001, created by apply step."

  - name: "Entry Level 2 - File 1.docx"
    id: "personal-file-level2-001"
    parent_id: "personal-folder-level1-001"
    permissions:
      - "personal-permission-current-user": "owner"

  - name: "Copy of Entry Level 2 - File 1.docx"
    id: "personal-file-level2-002"
    parent_id: "personal-folder-level1-001"
    permissions:
      - "personal-permission-current-user": "owner"
      - "personal-permission-other-user-1": "writer"
    notes:
      - "This is a copy of 'Entry Level 2 - File 1'."

  - name: "Entry Level 2 - File 3"
    id: "personal-file-level2-003"
    parent_id: "personal-folder-level1-001"
    permissions:
      - "personal-permission-current-user": "writer"
      - "personal-permission-other-user-1": "owner"

  - name: "Entry Level 2 - File 4"
    id: "personal-file-level2-004"
    parent_id: "personal-folder-level1-001"
    permissions:
      - "personal-permission-current-user": "owner"
      - "personal-permission-other-user-1": "writer"

  - name: "Entry Level 2 - File 3"
    id: "personal-file-level2-005"
    parent_id: "personal-folder-level1-001"
    permissions:
      - "personal-permission-current-user": "owner"
    notes:
      - "This is a copy of personal-file-level2-003, created by apply."

  - name: "Entry Level 3 - File 1"
    id: "personal-file-level3-001"
    parent_id: "personal-folder-level2-001"
    permissions:
      - "business-permission-other-user-1": "writer"
      - "personal-permission-other-user-1": "writer"
        "personal-permission-current-user": "owner"

  - name: "Entry Level 3 - File 2"
    id: "personal-file-level3-002"
    parent_id: "personal-folder-level2-001"
    permissions:
      - "personal-permission-other-user-1": "owner"
      - "personal-permission-other-user-2": "writer"
        "personal-permission-current-user": "writer"

  - name: "Entry Level 3 - File 3"
    id: "personal-file-level3-003"
    parent_id: "personal-folder-level2-002"
    permissions:
      - "personal-permission-current-user": "owner"
    notes:
      - "This is the pair for personal-file-level3-002, created by apply."

permissions:
  - id: "personal-permission-current-user"
    type: "user"
    email: "personal-current-user@example.com"
    name: "personal-current-user"

  - id: "personal-permission-other-user-1"
    type: "user"
    email: "personal-other-user-1@example.com"
    name: "personal-other-user-1"

  - id: "personal-permission-other-user-2"
    type: "user"
    email: "personal-other-user-2@example.com"
    name: "personal-other-user-2"

  - id: "business-permission-other-user-1"
    type: "user"
    email: "business-other-user-1@example.com"
    name: "business-other-user-1"
```