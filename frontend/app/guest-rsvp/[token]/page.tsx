import { GuestInviteResponsePage } from "../../../components/GuestInviteResponsePage";
import { PortalShell } from "../../../components/PortalShell";

type GuestRsvpPageProps = { params: Promise<{ token: string }> };

export default async function GuestRsvpPage({ params }: GuestRsvpPageProps) {
  const { token } = await params;
  return <PortalShell><GuestInviteResponsePage token={token} /></PortalShell>;
}
