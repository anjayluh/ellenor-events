from app.core.config import settings


def member_invitation_copy(invite_link: str) -> tuple[str, str]:
    return (
        "You're invited to plan with Ellenor Events",
        "Hello,\n\n"
        "You have been invited to join an Ellenor Events planning workspace. "
        "Open your invitation when you are ready to see the event details and accept your place on the planning team.\n\n"
        f"Open your invitation: {invite_link}\n\n"
        "If you were not expecting this invitation, you can safely ignore this email.\n\n"
        "Warmly,\nEllenor Events",
    )


def build_email_invite_payload(contact: str, invite_link: str) -> dict[str, str | None]:
    subject, body = member_invitation_copy(invite_link)
    return build_resend_email_payload(
        contact,
        subject,
        body,
    )


def guest_invitation_copy(recipient_name: str, event_title: str, rsvp_link: str) -> tuple[str, str]:
    return (
        f"Your invitation to {event_title}",
        f"Hello {recipient_name},\n\n"
        f"You have been invited to {event_title}. When you are ready, please use the link below to view the invitation and share your response.\n\n"
        f"View invitation and RSVP: {rsvp_link}\n\n"
        "We look forward to hearing from you.\n\n"
        "Warmly,\nEllenor Events",
    )


def meeting_notification_copy(action: str, meeting_title: str) -> tuple[str, str]:
    if action == "created":
        return (
            "A meeting has been added to your event",
            f"A new planning meeting, {meeting_title}, has been added to your Ellenor Events workspace.",
        )
    return (
        "A meeting has been updated",
        f"The planning meeting, {meeting_title}, has been updated in your Ellenor Events workspace.",
    )


def build_resend_email_payload(contact: str | None, subject: str, body: str) -> dict[str, str | None]:
    return {
        "provider": "resend",
        "from": settings.resend_from_email,
        "to": contact,
        "subject": subject,
        "body": body,
    }
