# Ellenor Events Email Templates

## Delivery boundaries

Ellenor Events currently has two email paths:

1. **Supabase Auth** sends account-confirmation and password-reset emails. On the free Supabase mailer, the subject and body are managed by Supabase and cannot be edited. These templates require custom SMTP before they can be branded.
2. **Ellenor Events notifications** prepare member invitations, guest RSVP invitations, and meeting updates through the configured email provider payload. The application owns the wording for these messages, but a delivery worker/provider is still required to send them.

## Supabase Auth: confirmation email

Configure this in Supabase Authentication → Emails → Confirm sign up when custom SMTP is available.

**Subject**

```text
Confirm your Ellenor Events account
```

**Body**

```html
<h2>Welcome to Ellenor Events</h2>

<p>Thank you for creating your account. Please confirm your email address to continue to your event planning workspace.</p>

<p><a href="{{ .ConfirmationURL }}">Confirm my email address</a></p>

<p>If you did not create an Ellenor Events account, you can safely ignore this email.</p>

<p>Warmly,<br>Ellenor Events</p>
```

## Supabase Auth: password reset

**Subject**

```text
Reset your Ellenor Events password
```

**Body**

```html
<h2>Reset your password</h2>

<p>We received a request to reset the password for your Ellenor Events account.</p>

<p><a href="{{ .ConfirmationURL }}">Choose a new password</a></p>

<p>If you did not request this, you can safely ignore this email.</p>

<p>Warmly,<br>Ellenor Events</p>
```

## Application-managed messages

The backend keeps these messages in `backend/app/services/email_service.py` so they remain consistent when a delivery provider is enabled:

- **Planning-team invitation:** You’re invited to plan with Ellenor Events.
- **Guest RSVP invitation:** Your invitation to `<event name>`.
- **Meeting update:** A meeting has been added to your event / A meeting has been updated.

Invitation emails should include a clear event context, one primary action, and a safe-ignore sentence. They should not mention Supabase, Resend, service credentials, internal IDs, or implementation details.

## Production setup

When ready to send branded Auth emails, configure a verified SMTP sender and set the sender name to **Ellenor Events**. Keep the application-owned message copy unchanged unless the product voice changes. Never put SMTP credentials in the repository or frontend bundle.
