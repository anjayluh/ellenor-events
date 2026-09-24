import Link from "next/link";

type EventCardProps = {
  id?: string;
  title: string;
  role: string;
  type: string;
  date: string;
  status?: string;
  onOpen?: () => void;
};

export function EventCard({ id, title, role, type, date, status, onOpen }: EventCardProps) {
  const content = (
    <>
      <div className="cardTitleRow">
        <h3>{title}</h3>
        {status ? <span className="badge softBadge">{status.replaceAll("_", " ")}</span> : null}
      </div>
      <div className="meta">
        <span className="badge">{role}</span>
        <span>{type}</span>
        <span>{date}</span>
      </div>
      {id ? <span className="cardAction">Open Event →</span> : null}
    </>
  );

  if (!id) {
    return <article className="eventCard">{content}</article>;
  }

  return <Link className="eventCard clickableCard" href={`/events/${id}`} onClick={onOpen}>{content}</Link>;
}
