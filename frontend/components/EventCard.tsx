type EventCardProps = {
  title: string;
  role: string;
  type: string;
  date: string;
};

export function EventCard({ title, role, type, date }: EventCardProps) {
  return (
    <article className="eventCard">
      <h3>{title}</h3>
      <div className="meta">
        <span className="badge">{role}</span>
        <span>{type}</span>
        <span>{date}</span>
      </div>
    </article>
  );
}
