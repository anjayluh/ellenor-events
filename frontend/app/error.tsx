"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="main">
      <section className="panel stateBlock">
        <p className="eyebrow">Something went sideways</p>
        <h1>The portal could not load this view.</h1>
        <button className="primaryButton" onClick={reset}>Try again</button>
      </section>
    </main>
  );
}
