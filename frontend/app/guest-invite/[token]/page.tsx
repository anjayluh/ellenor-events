import { GuestInviteResponsePage } from "../../../components/GuestInviteResponsePage";
import { PortalShell } from "../../../components/PortalShell";

type GuestInvitePageProps = { params: Promise<{ token: string }> };

export default async function GuestInvitePage({ params }: GuestInvitePageProps) {
  const { token } = await params;
  return <PortalShell><GuestInviteResponsePage token={token} /></PortalShell>;
}
