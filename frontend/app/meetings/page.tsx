import { PortalShell } from "../../components/PortalShell";

const meetings = [
  { title: "Planning Meeting", type: "committee", time: "Saturday, 10:00 AM", agenda: "Budget, vendors, and family roles" },
  { title: "General Family Meeting", type: "family", time: "Sunday, 4:00 PM", agenda: "Introductions, RSVP reminders, and contributions" },
  { title: "Vendor Review", type: "vendor", time: "Wednesday, 6:30 PM", agenda: "Decor, catering, and photography updates" }
];

export default function MeetingsPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Meetings</p>
        <h1>Keep committees and family aligned without the chaos swirl.</h1>
        <p>Upcoming meetings, notes, decisions, and RSVP responses live here.</p>
      </section>

      <section className="grid threeColumns">
        {meetings.map((meeting) => (
          <article className="panel" key={meeting.title}>
            <p className="eyebrow">{meeting.type}</p>
            <h2>{meeting.title}</h2>
            <p>{meeting.time}</p>
            <p>{meeting.agenda}</p>
            <div className="buttonRow">
              <button className="primaryButton">Accept</button>
              <button className="ghostButton">Tentative</button>
              <button className="ghostButton">Decline</button>
            </div>
          </article>
        ))}
      </section>
    </PortalShell>
  );
}
