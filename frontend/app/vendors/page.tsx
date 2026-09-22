import { PortalShell } from "../../components/PortalShell";
import { VendorsClientPage } from "../../components/ProtectedPages";

export default function VendorsPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Vendors</p>
        <h1>Find and manage service providers for the selected event.</h1>
        <p>Open an event workspace to view vendor details shared with your account.</p>
      </section>
      <VendorsClientPage />
    </PortalShell>
  );
}
