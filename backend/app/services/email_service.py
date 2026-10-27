from html import escape
import re

from app.core.config import settings


def text_to_html(body: str) -> str:
    paragraphs = [paragraph for paragraph in body.split("\n\n") if paragraph.strip()]
    rendered_paragraphs = []
    for paragraph in paragraphs:
        escaped = escape(paragraph).replace(chr(10), "<br>")
        linked = re.sub(
            r"(https://[^\s<]+)",
            r'<a href="\1" style="color:#8f3f55;text-decoration:underline">Open Ellenor Events</a>',
            escaped,
        )
        rendered_paragraphs.append(f"<p style=\"margin:0 0 16px\">{linked}</p>")
    rendered = "".join(rendered_paragraphs)
    return (
        '<div style="background:#f7f3ef;padding:32px 16px;font-family:Arial,sans-serif;line-height:1.6;color:#24201d">'
        '<div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #eadfd7;border-radius:16px;padding:32px">'
        '<div style="color:#8f3f55;font-size:12px;letter-spacing:1.6px;text-transform:uppercase;margin-bottom:24px">Ellenor Events</div>'
        f"{rendered}"
        '<p style="margin:24px 0 0;color:#756b65;font-size:13px">Plan beautifully, together.</p>'
        "</div></div>"
    )


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
        "provider": settings.email_provider,
        "from": settings.resend_from_email,
        "to": contact,
        "subject": subject,
        "body": body,
        "html": text_to_html(body),
    }
