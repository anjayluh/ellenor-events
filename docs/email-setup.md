# Ellenor Events email delivery

## What is implemented

Member invitations, guest RSVP invitations, and meeting notifications use the shared backend notification service. The service renders branded HTML and plain-text content, sends through the configured provider, records the provider message ID, and records whether the provider accepted or rejected the message.

Provider acceptance is not the same as inbox delivery. Delivery, bounce, complaint, and spam outcomes require provider event tracking and a controlled real-email check.

The QA provider is `mock`. It is deterministic and is used by automated tests and local QA only. Production rejects `EMAIL_PROVIDER=mock`.

## Resend configuration

The production provider is Resend:

```text
EMAIL_PROVIDER=resend
RESEND_API_KEY=<server-side secret>
RESEND_FROM_EMAIL=Ellenor Events <noreply@your-verified-domain.example>
RESEND_API_BASE_URL=https://api.resend.com
EMAIL_DELIVERY_TIMEOUT_SECONDS=10
```

The API key is server-only. Do not put it in `NEXT_PUBLIC_*` variables, frontend code, source control, or chat messages.

Resend requires a verified sender/domain before production delivery. Add the domain in the Resend dashboard, copy the exact SPF/DKIM records Resend provides into the DNS provider for that domain, and check the domain status in Resend. Do not add a second SPF record if the domain already has one; merge the required mechanism into the existing SPF policy. Add or review DMARC separately with the domain owner.

The repository does not contain an authenticated Resend account or live DNS values, so those values cannot be verified here and no provider credentials have been configured.

Official references:

- [Resend introduction](https://resend.com/docs/introduction)
- [Resend domain management](https://resend.com/docs/dashboard/domains/introduction)
- [Resend sending email](https://resend.com/docs/send-with-nodejs)
- [Resend webhooks](https://resend.com/docs/dashboard/webhooks/introduction)

## Environment and deployment

Set the variables above in the backend deployment environment only, then redeploy the backend. Keep QA/preview on `EMAIL_PROVIDER=mock` unless a verified non-production sender is intentionally configured. Set `EMAIL_PROVIDER=resend` only when the Resend key and sender are ready.

If the key is missing or Resend rejects a message, the API records a failed/retry-scheduled notification and returns a clear delivery error. It does not report the message as sent.

## Safe QA

Use `EMAIL_PROVIDER=mock` outside production. Invite creation, guest RSVP invitation, and meeting notification routes all use the normal notification lifecycle while the mock provider returns a deterministic message ID. Tests never call Resend.

## Controlled production verification

After configuring a verified sender, send one invitation to a recipient who has explicitly agreed to receive the test. Confirm all of the following:

1. The API response succeeds.
2. The notification record is `sent` with a provider message ID.
3. Resend shows the message as accepted and, where available, delivered.
4. The recipient mailbox receives the message and the links open the deployed application.

Do not treat an accepted API response as proof of inbox placement. Inspect spam/junk classification and provider delivery events separately.

## Remaining setup actions

1. Create or access the Ellenor Events Resend account.
2. Verify the actual sending domain and publish the exact SPF/DKIM records shown by Resend.
3. Review DMARC with the domain owner.
4. Create a restricted server-side API key.
5. Configure the variables in the backend deployment environment.
6. Perform one controlled real-recipient test.

Until these actions are complete, the application code is delivery-ready but real outbound email is not configured or verified.
