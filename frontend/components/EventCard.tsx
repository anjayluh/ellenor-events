import Link from "next/link";

type EventCardProps = {
  id?: string;
  title: string;
  role: string;
  type: string;
  date: string;
};

export function EventCard({ id, title, role, type, date }: EventCardProps) {
  const content = (
    <>
      <h3>{title}</h3>
      <div className="meta">
        <span className="badge">{role}</span>
        <span>{type}</span>
        <span>{date}</span>
      </div>
    </>
  );

  if (!id) {
    return <article className="eventCard">{content}</article>;
  }

  return <Link className="eventCard clickableCard" href={`/events/${id}`}>{content}</Link>;
}
