import { InviteAcceptance } from "../../../components/InviteAcceptance";
import { PortalShell } from "../../../components/PortalShell";

type InvitePageProps = {
  params: Promise<{ token: string }>;
};

export default async function InvitePage({ params }: InvitePageProps) {
  const { token } = await params;

  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Invitation</p>
        <h1>You have been invited to help coordinate an event.</h1>
        <p>Confirm your details to link this invite to your Ellenor Events account. The invite token is never shown on the page.</p>
      </section>
      <InviteAcceptance token={token} />
    </PortalShell>
  );
}
