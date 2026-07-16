"use client";

import { FormEvent, useMemo, useState } from "react";
import { apiPost } from "../lib/api";

type InviteAcceptRead = { status: string; project_id: string; user_id: string; role: string };

export function InviteAcceptance({ token }: { token: string }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("anjayluh.wakabi@gmail.com");
  const [message, setMessage] = useState("Confirm your details to accept this invite.");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [accepted, setAccepted] = useState<InviteAcceptRead | null>(null);

  const isValid = useMemo(() => name.trim().length >= 2 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email), [name, email]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const result = await apiPost<InviteAcceptRead, { token: string; name: string; email: string }>("/invites/accept", { token, name, email });
      setAccepted(result);
      setMessage(`Invite accepted as ${result.role.replaceAll('_', ' ')}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not accept invite.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (accepted) {
    return <section className="panel"><h2>Invite accepted</h2><p>{message}</p><p>Project ID: {accepted.project_id}</p></section>;
  }

  return (
    <form className="panel stack" onSubmit={submit}>
      <label>
        Full name
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Your full name" />
      </label>
      <label>
        Email
        <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" />
      </label>
      <button className="primaryButton" disabled={!isValid || isSubmitting} type="submit">
        {isSubmitting ? "Accepting..." : "Accept invite"}
      </button>
      <p>{message}</p>
    </form>
  );
}
