import { PortalShell } from "../../components/PortalShell";
import { TasksClientPage } from "../../components/TasksClientPage";

export default function TasksPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Tasks</p>
        <h1>Coordinate event responsibilities with calm clarity.</h1>
        <p>Create, assign, and track the work that keeps the event moving without turning planning into a generic project-management board.</p>
      </section>
      <TasksClientPage />
    </PortalShell>
  );
}
