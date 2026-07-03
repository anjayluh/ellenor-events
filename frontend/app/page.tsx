import { BudgetPreview } from "../components/BudgetPreview";
import { EventCard } from "../components/EventCard";
import { PortalShell } from "../components/PortalShell";

const events = [
  { title: "Wedding - John & Mary", role: "PARTNER", type: "wedding", date: "2026-09-12" },
  { title: "Introduction - Sarah", role: "FAMILY_VIEWER", type: "introduction", date: "2026-08-03" },
  { title: "Wedding - Peter & Jane", role: "COMMITTEE_CHAIR", type: "wedding", date: "2026-10-20" }
];

export default function Home() {
  return (
    <PortalShell>
      <section className="hero">
        <p className="eyebrow">Ellenor Events Coordination System</p>
        <h1>A calm command center for ceremonies with many moving parts.</h1>
        <p>
          Coordinate weddings, introductions, committees, meetings, RSVP flows, contributions,
          and budget visibility without exposing sensitive details to the wrong role.
        </p>
      </section>

      <section className="grid twoColumns">
        <div className="panel">
          <h2>Your Events</h2>
          <div className="stack">
            {events.map((event) => (
              <EventCard key={event.title} {...event} />
            ))}
          </div>
        </div>
        <BudgetPreview visibility="SUMMARY_ACCESS" />
      </section>
    </PortalShell>
  );
}
