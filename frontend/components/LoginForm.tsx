"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiPost } from "../lib/api";
import { saveSession } from "../lib/session";
import type { AuthToken } from "../lib/types";

type Mode = "login" | "register";

export function LoginForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("anjayluh.wakabi@gmail.com");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("Sign in with your email and password.");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const emailError = email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? "Enter a valid email address." : "";
  const passwordError = password && password.length < 8 ? "Password must be at least 8 characters." : "";
  const nameError = mode === "register" && name && name.trim().length < 2 ? "Display name must be at least 2 characters." : "";

  const isValid = useMemo(() => {
    const hasEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    const hasPassword = password.length >= 8;
    const hasNameIfRegistering = mode === "login" || name.trim().length >= 2;
    return hasEmail && hasPassword && hasNameIfRegistering && !emailError && !passwordError && !nameError;
  }, [email, password, name, mode, emailError, passwordError, nameError]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || isSubmitting) return;

    setIsSubmitting(true);
    setMessage(mode === "login" ? "Signing you in..." : "Creating your account...");
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const payload = mode === "login" ? { email, password } : { email, password, name };
      const result = await apiPost<AuthToken | { detail?: string; message?: string }, typeof payload>(path, payload);
      if (!("access_token" in result)) {
        setMessage(result.detail ?? result.message ?? "Account created. Confirm your email before signing in.");
        return;
      }
      saveSession(result);
      setMessage(`Signed in as ${result.user.name ?? result.user.email}. Taking you to your workspace...`);
      router.replace("/");
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
          <label className="formField">
            Display name
            <input value={name} onBlur={() => setTouched((current) => ({ ...current, name: true }))} onChange={(event) => setName(event.target.value)} placeholder="Your full name" autoComplete="name" aria-invalid={Boolean(nameError)} />
            <span className="helperText">At least 2 characters, so family and committee members can recognize you.</span>
            {touched.name && nameError ? <span className="errorText">{nameError}</span> : null}
          </label>
        ) : null}
        <label className="formField">
          Email
          <input value={email} onBlur={() => setTouched((current) => ({ ...current, email: true }))} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" type="email" autoComplete="email" aria-invalid={Boolean(emailError)} />
          <span className="helperText">Use the email connected to your Supabase account or invitation.</span>
          {touched.email && emailError ? <span className="errorText">{emailError}</span> : null}
        </label>
        <label className="formField">
          Password
          <input value={password} onBlur={() => setTouched((current) => ({ ...current, password: true }))} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} aria-invalid={Boolean(passwordError)} />
          <span className="helperText">Minimum 8 characters. If your email is unconfirmed, Supabase will block sign-in.</span>
          {touched.password && passwordError ? <span className="errorText">{passwordError}</span> : null}
        </label>
        <button className="primaryButton" disabled={!isValid || isSubmitting} type="submit">
          {isSubmitting ? (mode === "login" ? "Signing in..." : "Creating...") : (mode === "login" ? "Sign in" : "Create account")}
        </button>
      </form>

      <p>{message}</p>
    </div>
  );
}
