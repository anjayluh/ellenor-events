import { PortalShell } from "../../components/PortalShell";

const vendors = [
  { name: "Kampala Decor House", category: "Decor", status: "contacted", contact: "+256700000301" },
  { name: "Pearl Gardens Catering", category: "Catering", status: "shortlisted", contact: "+256700000302" },
  { name: "Nile Lens Studio", category: "Photography", status: "confirmed", contact: "+256700000303" }
];

export default function VendorsPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Vendors</p>
        <h1>A simple directory before it becomes a marketplace.</h1>
        <p>Track vendor category, status, contacts, notes, and external links without requiring accounts.</p>
      </section>

      <section className="grid threeColumns">
        {vendors.map((vendor) => (
          <article className="panel" key={vendor.name}>
            <p className="eyebrow">{vendor.category}</p>
            <h2>{vendor.name}</h2>
            <p>Status: {vendor.status}</p>
            <p>Contact: {vendor.contact}</p>
          </article>
        ))}
      </section>
    </PortalShell>
  );
}
