export function StateBlock({ title, message }: { title: string; message: string }) {
  return (
    <section className="panel stateBlock">
      <p className="eyebrow">Portal State</p>
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}
