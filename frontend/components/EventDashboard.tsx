import { BudgetPreview } from "./BudgetPreview";
import { RoleAwareNav } from "./RoleAwareNav";
import type { Project } from "../lib/types";

const meetings = ["Planning Meeting", "General Family Meeting", "Vendor Review"];
const tasks = ["Confirm decor quote", "Collect family RSVP list", "Finalize meeting notes"];
const vendors = ["Kampala Decor House", "Pearl Gardens Catering", "Nile Lens Studio"];

export function EventDashboard({ project }: { project: Project }) {
  const role = project.role ?? "FAMILY_VIEWER";
  const visibility = project.budget_visibility_mode ?? "CONTRIBUTION_ONLY";

  return (
    <>
      <section className="hero compact">
        <p className="eyebrow">{project.type} dashboard</p>
        <h1>{project.title}</h1>
        <p>
          Role: {role.replaceAll("_", " ")} · Event date: {project.event_date ?? "To be confirmed"}
        </p>
      </section>

      <RoleAwareNav role={role} projectId={project.id} />

      <section className="grid twoColumns" id="overview">
        <article className="panel">
          <p className="eyebrow">Overview</p>
          <h2>Coordination Snapshot</h2>
          <p>Status: {project.status}</p>
          <p>Linked ceremony views, role-based navigation, and mobile-first tabs start here.</p>
        </article>
        <BudgetPreview visibility={visibility} />
      </section>

      <section className="grid threeColumns" id="meetings">
        {meetings.map((meeting) => <article className="panel" key={meeting}><p className="eyebrow">Meeting</p><h2>{meeting}</h2><p>RSVP controls appear for authenticated members.</p></article>)}
      </section>

      <section className="grid threeColumns" id="committee">
        {tasks.map((task) => <article className="panel" key={task}><p className="eyebrow">Task</p><h2>{task}</h2><p>Assigned committee work stays project-scoped.</p></article>)}
      </section>

      <section className="grid threeColumns" id="vendors">
        {vendors.map((vendor) => <article className="panel" key={vendor}><p className="eyebrow">Vendor</p><h2>{vendor}</h2><p>Directory records do not require user accounts.</p></article>)}
      </section>
    </>
  );
}
