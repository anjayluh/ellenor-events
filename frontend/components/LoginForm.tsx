"use client";

import { FormEvent, useState } from "react";
import { apiPost } from "../lib/api";
import { saveSession } from "../lib/session";
import type { AuthToken } from "../lib/types";

type LoginChallenge = {
  status: string;
  channel: string;
  contact: string;
  development_code?: string | null;
  development_magic_link?: string | null;
};

export function LoginForm() {
  const [contact, setContact] = useState("+256700000101");
  const [name, setName] = useState("Amina Owner");
  const [code, setCode] = useState("000000");
  const [challenge, setChallenge] = useState<LoginChallenge | null>(null);
  const [message, setMessage] = useState("Use the development OTP while production Supabase Auth is being connected.");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function requestLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = contact.includes("@") ? { email: contact } : { phone: contact };
      const result = await apiPost<LoginChallenge, typeof payload>("/auth/login", payload);
      setChallenge(result);
      setMessage(`Verification sent by ${result.channel}.`);
    } catch {
      setChallenge({ status: "demo", channel: contact.includes("@") ? "email" : "phone", contact, development_code: "000000" });
      setMessage("API is offline, so the demo login flow is active.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function verifyOtp() {
    setIsSubmitting(true);
    try {
      const result = await apiPost<AuthToken, { contact: string; code: string; name: string }>("/auth/verify-otp", {
        contact,
        code,
        name
      });
      saveSession(result);
      setMessage(`Signed in as ${result.user.name ?? result.user.phone ?? result.user.email}.`);
    } catch {
      saveSession({
        access_token: "demo-token",
        token_type: "bearer",
        user: { id: "00000000-0000-0000-0000-000000000101", name, phone: contact.includes("@") ? null : contact, email: contact.includes("@") ? contact : null }
      });
      setMessage("Demo session saved. Start the backend to use real OTP verification.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="panel authPanel">
      <form className="stack" onSubmit={requestLogin}>
        <label>
          Phone or email
          <input value={contact} onChange={(event) => setContact(event.target.value)} placeholder="+256700000101" />
        </label>
        <label>
          Display name
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Amina Owner" />
        </label>
        <button className="primaryButton" disabled={isSubmitting} type="submit">
          Request OTP / magic link
        </button>
      </form>

      {challenge ? (
        <div className="stack authChallenge">
          <p>{message}</p>
          {challenge.development_code ? <p className="tokenNote">Development code: {challenge.development_code}</p> : null}
          {challenge.development_magic_link ? <p className="tokenNote">{challenge.development_magic_link}</p> : null}
          <label>
            Verification code
            <input value={code} onChange={(event) => setCode(event.target.value)} />
          </label>
          <button className="secondaryButton light" disabled={isSubmitting} type="button" onClick={verifyOtp}>
            Verify and continue
          </button>
        </div>
      ) : (
        <p>{message}</p>
      )}
    </div>
  );
}
