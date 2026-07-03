import { BudgetPreview } from "../components/BudgetPreview";
import { EventCard } from "../components/EventCard";
import { PortalShell } from "../components/PortalShell";
import { StateBlock } from "../components/StateBlock";
import { apiGet } from "../lib/api";
import { demoProjects } from "../lib/demo-data";
import type { Project } from "../lib/types";

async function getProjects(): Promise<{ projects: Project[]; isDemo: boolean }> {
  try {
    return { projects: await apiGet<Project[]>("/projects"), isDemo: false };
  } catch {
    return { projects: demoProjects, isDemo: true };
  }
}

export default async function Home() {
  const { projects, isDemo } = await getProjects();

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

      {isDemo ? <StateBlock title="Demo mode" message="Start the FastAPI backend and sign in to load live project data." /> : null}

      <section className="grid twoColumns">
        <div className="panel">
          <h2>Your Events</h2>
          <div className="stack">
            {projects.map((event) => (
              <EventCard
                key={event.id}
                id={event.id}
                title={event.title}
                role={event.role ?? "FAMILY_VIEWER"}
                type={event.type}
                date={event.event_date ?? "TBC"}
              />
            ))}
          </div>
        </div>
        <BudgetPreview visibility={projects[0]?.budget_visibility_mode ?? "SUMMARY_ACCESS"} />
      </section>
    </PortalShell>
  );
}
