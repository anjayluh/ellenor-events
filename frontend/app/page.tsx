import { CustomerDashboard } from "../components/CustomerDashboard";
import { PortalShell } from "../components/PortalShell";

export default function Home() {
  return (
    <PortalShell>
      <CustomerDashboard />
    </PortalShell>
  );
}
