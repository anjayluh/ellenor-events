import { PortalShell } from "../../components/PortalShell";

const tasks = [
  { title: "Confirm decor quote", owner: "Grace Chair", status: "in progress", due: "2026-08-01" },
  { title: "Collect family RSVP list", owner: "Sarah Viewer", status: "todo", due: "2026-08-04" },
  { title: "Finalize meeting notes", owner: "David Partner", status: "done", due: "2026-08-06" }
];

export default function CommitteePage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Committee</p>
        <h1>Tasks, ownership, and decisions in one place.</h1>
        <p>Assign work to project members and keep ceremony coordination moving without losing the thread.</p>
      </section>

      <section className="grid threeColumns">
        {tasks.map((task) => (
          <article className="panel" key={task.title}>
            <p className="eyebrow">{task.status}</p>
            <h2>{task.title}</h2>
            <p>Owner: {task.owner}</p>
            <p>Due: {task.due}</p>
          </article>
        ))}
      </section>
    </PortalShell>
  );
}
