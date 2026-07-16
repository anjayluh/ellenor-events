import { PortalShell } from "../../components/PortalShell";
import { VendorsClientPage } from "../../components/ProtectedPages";

export default function VendorsPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Vendors</p>
        <h1>A simple directory before it becomes a marketplace.</h1>
        <p>Vendor contact details are shown only to authenticated project members.</p>
      </section>
      <VendorsClientPage />
    </PortalShell>
  );
}
