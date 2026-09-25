from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.customer_account import AccountEntitlement
from app.models.project_guest import ProjectGuest, ProjectGuestInvitation

from conftest import auth_headers, create_project_with_member, create_user


def grant_guest_entitlements(db: Session, project, *, guests: int | None = 3, emails: int | None = 2):
    db.add(AccountEntitlement(customer_account_id=project.customer_account_id, key="guests_per_event", quantity=guests, used_quantity=0, status="ACTIVE", metadata_json={"source": "PAID"}))
    db.add(AccountEntitlement(customer_account_id=project.customer_account_id, key="invitation_emails_per_month", quantity=emails, used_quantity=0, status="ACTIVE", metadata_json={"source": "PAID"}))
    db.flush()


def guest_payload(**overrides):
    payload = {
        "first_name": "Auntie",
        "last_name": "Rose",
        "email": "auntie.rose@example.com",
        "phone": "+256700111222",
        "category": "Bride family",
        "group_name": "VIP table",
        "notes": "Needs front seating",
    }
    payload.update(overrides)
    return payload


def test_project_guest_crud_search_filter_and_authorization(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    outsider = create_user(db_session, name="Outsider")
    project = create_project_with_member(db_session, owner, title="Guest Wedding")
    grant_guest_entitlements(db_session, project)
    db_session.commit()

    denied = client.get(f"/projects/{project.id}/guests", headers=auth_headers(outsider))
    assert denied.status_code == 403

    created = client.post(f"/projects/{project.id}/guests", headers=auth_headers(owner), json=guest_payload())
    assert created.status_code == 200
    guest_id = created.json()["id"]
    assert created.json()["display_name"] == "Auntie Rose"

    filtered = client.get(f"/projects/{project.id}/guests?search=rose&category=Bride family", headers=auth_headers(owner))
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    updated = client.patch(f"/projects/{project.id}/guests/{guest_id}", headers=auth_headers(owner), json={"rsvp_status": "ATTENDING", "group_name": "Family VIP"})
    assert updated.status_code == 200
    assert updated.json()["rsvp_status"] == "ATTENDING"
    assert updated.json()["rsvp_responded_at"] is not None

    deleted = client.delete(f"/projects/{project.id}/guests/{guest_id}", headers=auth_headers(owner))
    assert deleted.status_code == 200
    assert client.get(f"/projects/{project.id}/guests", headers=auth_headers(owner)).json() == []


def test_guest_limit_is_enforced_without_hardcoded_package_values(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Small Guest Wedding")
    grant_guest_entitlements(db_session, project, guests=1)
    db_session.commit()

    first = client.post(f"/projects/{project.id}/guests", headers=auth_headers(owner), json=guest_payload(email="one@example.com"))
    assert first.status_code == 200

    second = client.post(f"/projects/{project.id}/guests", headers=auth_headers(owner), json=guest_payload(email="two@example.com"))
    assert second.status_code == 402
    assert second.json()["detail"]["code"] == "GUEST_ENTITLEMENT_REQUIRED"

    summary = client.get(f"/projects/{project.id}/guests/summary", headers=auth_headers(owner))
    assert summary.status_code == 200
    assert summary.json()["guest_usage"] == {"key": "guests_per_event", "used": 1, "limit": 1, "remaining": 0, "label": "Guests"}


def test_invitation_requires_email_consumes_quota_and_is_idempotent(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Invitation Wedding")
    grant_guest_entitlements(db_session, project, guests=3, emails=1)
    db_session.commit()

    no_email = client.post(f"/projects/{project.id}/guests", headers=auth_headers(owner), json=guest_payload(email=None, phone="+256700999888"))
    assert no_email.status_code == 200
    no_email_send = client.post(f"/projects/{project.id}/guests/{no_email.json()['id']}/invite", headers=auth_headers(owner), json={})
    assert no_email_send.status_code == 409

    guest = client.post(f"/projects/{project.id}/guests", headers=auth_headers(owner), json=guest_payload(email="invite@example.com"))
    sent = client.post(f"/projects/{project.id}/guests/{guest.json()['id']}/invite", headers=auth_headers(owner), json={})
    assert sent.status_code == 200
    assert sent.json()["already_sent"] is False
    assert sent.json()["invitation_email_usage"]["used"] == 1

    replay = client.post(f"/projects/{project.id}/guests/{guest.json()['id']}/invite", headers=auth_headers(owner), json={})
    assert replay.status_code == 200
    assert replay.json()["already_sent"] is True
    assert replay.json()["invitation_email_usage"]["used"] == 1
    assert db_session.query(ProjectGuestInvitation).filter(ProjectGuestInvitation.project_guest_id == UUID(guest.json()["id"])).count() == 1

    resend = client.post(f"/projects/{project.id}/guests/{guest.json()['id']}/invite", headers=auth_headers(owner), json={"resend": True})
    assert resend.status_code == 402
    assert resend.json()["detail"]["code"] == "INVITATION_EMAIL_ENTITLEMENT_REQUIRED"


def test_public_guest_rsvp_token_flow_is_scoped(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Public RSVP Wedding")
    grant_guest_entitlements(db_session, project)
    db_session.commit()

    guest = client.post(f"/projects/{project.id}/guests", headers=auth_headers(owner), json=guest_payload(email="public@example.com"))
    sent = client.post(f"/projects/{project.id}/guests/{guest.json()['id']}/invite", headers=auth_headers(owner), json={})
    token = sent.json()["invitation"]["token"]

    preview = client.get(f"/guest-rsvps/{token}")
    assert preview.status_code == 200
    assert preview.json()["event_title"] == "Public RSVP Wedding"
    assert "customer_account_id" not in preview.json()

    invalid = client.post(f"/guest-rsvps/{uuid4().hex}/respond", json={"rsvp_status": "ATTENDING"})
    assert invalid.status_code == 404

    response = client.post(f"/guest-rsvps/{token}/respond", json={"rsvp_status": "ATTENDING", "rsvp_attendee_count": 2, "rsvp_note": "Vegetarian meal, please"})
    assert response.status_code == 200
    assert response.json()["rsvp_status"] == "ATTENDING"
    assert response.json()["rsvp_attendee_count"] == 2
    assert response.json()["rsvp_note"] == "Vegetarian meal, please"
    assert response.json()["responded_at"] is not None

    changed = client.post(f"/guest-rsvps/{token}/respond", json={"rsvp_status": "NOT_ATTENDING", "rsvp_note": "Travel changed"})
    assert changed.status_code == 200
    assert changed.json()["rsvp_status"] == "NOT_ATTENDING"
    assert changed.json()["rsvp_attendee_count"] == 0

    stored_guest = db_session.query(ProjectGuest).filter(ProjectGuest.id == UUID(guest.json()["id"])).one()
    assert stored_guest.rsvp_note == "Travel changed"

    summary = client.get(f"/projects/{project.id}/guests/summary", headers=auth_headers(owner))
    assert summary.json()["attending"] == 0
    assert summary.json()["not_attending"] == 1
    assert summary.json()["responded"] == 1
    assert summary.json()["rsvp_responses"] == 1
    assert summary.json()["invitations_opened"] == 1


def test_guest_summary_counts_distinct_guests_not_invitation_history(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="Summary Wedding")
    grant_guest_entitlements(db_session, project, guests=5, emails=5)
    db_session.commit()

    guest = client.post(f"/projects/{project.id}/guests", headers=auth_headers(owner), json=guest_payload(email="summary@example.com"))
    assert guest.status_code == 200
    first_send = client.post(f"/projects/{project.id}/guests/{guest.json()['id']}/invite", headers=auth_headers(owner), json={})
    assert first_send.status_code == 200
    preview = client.get(f"/guest-rsvps/{first_send.json()['invitation']['token']}")
    assert preview.status_code == 200

    resend = client.post(f"/projects/{project.id}/guests/{guest.json()['id']}/invite", headers=auth_headers(owner), json={"resend": True})
    assert resend.status_code == 200
    assert db_session.query(ProjectGuestInvitation).filter(ProjectGuestInvitation.project_guest_id == UUID(guest.json()["id"])).count() == 2

    summary = client.get(f"/projects/{project.id}/guests/summary", headers=auth_headers(owner))
    assert summary.status_code == 200
    assert summary.json()["total"] == 1
    assert summary.json()["invitation_sent"] == 1
    assert summary.json()["opened"] == 1
    assert summary.json()["invitations_opened"] == 1
    assert summary.json()["pending_rsvp"] == 1
    assert summary.json()["invitation_email_usage"]["used"] == 2


def test_guest_from_another_project_cannot_be_modified(client, db_session: Session):
    owner = create_user(db_session, name="Owner")
    project = create_project_with_member(db_session, owner, title="First")
    other_project = create_project_with_member(db_session, owner, title="Second")
    grant_guest_entitlements(db_session, project)
    grant_guest_entitlements(db_session, other_project)
    db_session.commit()

    guest = client.post(f"/projects/{project.id}/guests", headers=auth_headers(owner), json=guest_payload(email="cross@example.com"))
    assert guest.status_code == 200

    wrong_project_update = client.patch(f"/projects/{other_project.id}/guests/{guest.json()['id']}", headers=auth_headers(owner), json={"first_name": "Wrong"})
    assert wrong_project_update.status_code == 404
