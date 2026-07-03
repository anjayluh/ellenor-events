import { PortalShell } from "../../../components/PortalShell";

type InvitePageProps = {
  params: Promise<{ token: string }>;
};

export default async function InvitePage({ params }: InvitePageProps) {
  const { token } = await params;
  const inviteLink = `/invite/${token}`;
  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(
    `I received my Ellenor Events invite: ${inviteLink}`
  )}`;

  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Invitation</p>
        <h1>You have been invited to help coordinate an event.</h1>
        <p>
          Open this invite, confirm your name and contact, then Ellenor will link you to the
          event role assigned by the host.
        </p>
        <div className="buttonRow">
          <a className="primaryButton" href={whatsappUrl}>Continue with WhatsApp</a>
          <a className="secondaryButton" href={`mailto:?subject=Ellenor Events invite&body=${encodeURIComponent(inviteLink)}`}>
            Use email fallback
          </a>
        </div>
        <p className="tokenNote">Invite token: {token}</p>
      </section>
    </PortalShell>
  );
}
