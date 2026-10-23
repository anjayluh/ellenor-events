import Link from "next/link";

export function StateBlock({ title, message, action }: { title: string; message: string; action?: { href: string; label: string } }) {
  return (
    <section className="panel stateBlock">
      <p className="eyebrow">Ellenor Events</p>
      <h2>{title}</h2>
      <p>{message}</p>
      {action ? <div className="buttonRow compactButtons"><Link className="primaryButton" href={action.href}>{action.label}</Link></div> : null}
    </section>
  );
}
