import { PortalShell } from "../../../components/PortalShell";

export default function InvitePage({ params }: { params: { token: string } }) {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Invitation</p>
        <h1>You have been invited to help coordinate an event.</h1>
        <p>Secure token: {params.token}</p>
        <button className="primaryButton">Accept invite</button>
      </section>
    </PortalShell>
  );
}
