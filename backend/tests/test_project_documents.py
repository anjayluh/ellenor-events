from uuid import uuid4

from app.api import documents as documents_api
from app.models import ProjectMember
from tests.conftest import auth_headers, create_project_with_member, create_user


class FakeDocumentStorage:
    def __init__(self):
        self.uploaded: dict[str, bytes] = {}

    def upload(self, path: str, content: bytes, mime_type: str) -> None:
        self.uploaded[path] = content

    def sign(self, path: str, expires_in: int) -> str:
        return f"https://storage.test/{path}?expires={expires_in}"

    def delete(self, path: str) -> None:
        self.uploaded.pop(path, None)


def test_document_upload_list_preview_and_archive(client, db_session, monkeypatch):
    owner = create_user(db_session, email="documents-owner@example.com")
    project = create_project_with_member(db_session, owner)
    storage = FakeDocumentStorage()
    monkeypatch.setattr(documents_api, "storage_client", storage)

    response = client.post(
        f"/projects/{project.id}/documents",
        headers=auth_headers(owner),
        data={"category": "CONTRACT", "description": "Venue agreement"},
        files={"file": ("venue.pdf", b"contract-content", "application/pdf")},
    )
    assert response.status_code == 201
    document = response.json()
    assert document["category"] == "CONTRACT"
    assert document["file_size_bytes"] == len(b"contract-content")
    assert len(storage.uploaded) == 1

    listed = client.get(f"/projects/{project.id}/documents?category=CONTRACT", headers=auth_headers(owner))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [document["id"]]

    preview = client.get(f"/projects/{project.id}/documents/{document['id']}/url", headers=auth_headers(owner))
    assert preview.status_code == 200
    assert "storage.test" in preview.json()["url"]

    archived = client.delete(f"/projects/{project.id}/documents/{document['id']}", headers=auth_headers(owner))
    assert archived.status_code == 200
    assert archived.json() == {"status": "archived"}
    assert client.get(f"/projects/{project.id}/documents", headers=auth_headers(owner)).json() == []
    assert len(client.get(f"/projects/{project.id}/documents?include_archived=true", headers=auth_headers(owner)).json()) == 1


def test_document_upload_rejects_unsupported_file_type(client, db_session, monkeypatch):
    owner = create_user(db_session)
    project = create_project_with_member(db_session, owner)
    monkeypatch.setattr(documents_api, "storage_client", FakeDocumentStorage())

    response = client.post(
        f"/projects/{project.id}/documents",
        headers=auth_headers(owner),
        data={"category": "OTHER"},
        files={"file": ("malware.exe", b"not executable", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_document_access_is_project_scoped(client, db_session, monkeypatch):
    owner = create_user(db_session)
    outsider = create_user(db_session)
    project = create_project_with_member(db_session, owner)
    other_project = create_project_with_member(db_session, outsider, title="Other event")
    monkeypatch.setattr(documents_api, "storage_client", FakeDocumentStorage())

    created = client.post(
        f"/projects/{project.id}/documents",
        headers=auth_headers(owner),
        data={"category": "PLANNING"},
        files={"file": ("plan.png", b"image-content", "image/png")},
    )
    document_id = created.json()["id"]
    denied = client.get(f"/projects/{other_project.id}/documents/{document_id}", headers=auth_headers(outsider))
    assert denied.status_code == 404

    outsider_list = client.get(f"/projects/{project.id}/documents", headers=auth_headers(outsider))
    assert outsider_list.status_code == 403


def test_guest_viewer_cannot_access_documents(client, db_session):
    owner = create_user(db_session)
    viewer = create_user(db_session)
    project = create_project_with_member(db_session, owner)
    db_session.add(ProjectMember(project_id=project.id, user_id=viewer.id, role="GUEST_VIEWER"))
    db_session.commit()

    response = client.get(f"/projects/{project.id}/documents", headers=auth_headers(viewer))
    assert response.status_code == 403
