"use client";

import { FormEvent, useMemo, useState } from "react";
import { apiPost } from "../lib/api";
import { saveSession } from "../lib/session";
import type { AuthToken } from "../lib/types";

type Mode = "login" | "register";

export function LoginForm() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("anjayluh.wakabi@gmail.com");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("Sign in with your email and password.");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isValid = useMemo(() => {
    const hasEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    const hasPassword = password.length >= 8;
    const hasNameIfRegistering = mode === "login" || name.trim().length >= 2;
    return hasEmail && hasPassword && hasNameIfRegistering;
  }, [email, password, name, mode]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || isSubmitting) return;

    setIsSubmitting(true);
    setMessage(mode === "login" ? "Signing you in..." : "Creating your account...");
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const payload = mode === "login" ? { email, password } : { email, password, name };
      const result = await apiPost<AuthToken, typeof payload>(path, payload);
      saveSession(result);
      setMessage(`Signed in as ${result.user.name ?? result.user.email}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Authentication failed. Please check your details.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="panel authPanel">
      <div className="segmentedControl" aria-label="Authentication mode">
        <button className={mode === "login" ? "active" : ""} type="button" disabled={isSubmitting} onClick={() => setMode("login")}>Sign in</button>
        <button className={mode === "register" ? "active" : ""} type="button" disabled={isSubmitting} onClick={() => setMode("register")}>Create account</button>
      </div>

      <form className="stack" onSubmit={submit}>
        {mode === "register" ? (
          <label>
            Display name
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Your full name" autoComplete="name" />
          </label>
        ) : null}
        <label>
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" type="email" autoComplete="email" />
        </label>
        <label>
          Password
          <input value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} />
        </label>
        <button className="primaryButton" disabled={!isValid || isSubmitting} type="submit">
          {isSubmitting ? (mode === "login" ? "Signing in..." : "Creating...") : (mode === "login" ? "Sign in" : "Create account")}
        </button>
      </form>

      <p>{message}</p>
    </div>
  );
}
