"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiPost } from "../lib/api";
import { saveSession } from "../lib/session";
import type { AuthMessage, AuthToken } from "../lib/types";

type Mode = "login" | "register" | "reset";

export function LoginForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("anjayluh.wakabi@gmail.com");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("Sign in to continue to your Ellenor Events workspace.");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    if (params.get("type") === "recovery" && params.get("access_token")) {
      router.replace(`/reset-password${window.location.hash}`);
    }
  }, [router]);

  const emailError = email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? "Enter a valid email address." : "";
  const passwordError = password && password.length < 8 ? "Password must be at least 8 characters." : "";
  const nameError = mode === "register" && name && name.trim().length < 2 ? "Display name must be at least 2 characters." : "";

  const isValid = useMemo(() => {
    const hasEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    const hasPassword = mode === "reset" || password.length >= 8;
    const hasNameIfRegistering = mode !== "register" || name.trim().length >= 2;
    return hasEmail && hasPassword && hasNameIfRegistering && !emailError && !passwordError && !nameError;
  }, [email, password, name, mode, emailError, passwordError, nameError]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isValid || isSubmitting) return;

    setIsSubmitting(true);
    setMessage(mode === "reset" ? "Sending reset email..." : mode === "login" ? "Signing you in..." : "Creating your account...");
    try {
      if (mode === "reset") {
        const result = await apiPost<AuthMessage, { email: string }>("/auth/password-reset/request", { email });
        setMessage(result.message);
        return;
      }
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
      setMessage(error instanceof Error ? error.message : "Sign-in failed. Please check your details.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="panel authPanel">
      <div className="segmentedControl" aria-label="Account access options">
        <button className={mode === "login" ? "active" : ""} type="button" disabled={isSubmitting} onClick={() => setMode("login")}>Sign in</button>
        <button className={mode === "register" ? "active" : ""} type="button" disabled={isSubmitting} onClick={() => setMode("register")}>Create account</button>
        <button className={mode === "reset" ? "active" : ""} type="button" disabled={isSubmitting} onClick={() => setMode("reset")}>Reset password</button>
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
          <span className="helperText">Use the email connected to your Ellenor Events account or invitation.</span>
            {touched.email && emailError ? <span className="errorText">{emailError}</span> : null}
          </label>
        {mode === "reset" ? (
          <span className="helperText">We will email a secure reset link. Open it to choose a new password.</span>
        ) : (
          <label className="formField">
            Password
            <input value={password} onBlur={() => setTouched((current) => ({ ...current, password: true }))} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} aria-invalid={Boolean(passwordError)} />
            <span className="helperText">Minimum 8 characters. Use the password you created for Ellenor Events.</span>
            {touched.password && passwordError ? <span className="errorText">{passwordError}</span> : null}
          </label>
        )}
        <button className="primaryButton" disabled={!isValid || isSubmitting} type="submit">
          {isSubmitting ? (mode === "reset" ? "Sending..." : mode === "login" ? "Signing in..." : "Creating...") : (mode === "reset" ? "Send reset link" : mode === "login" ? "Sign in" : "Create account")}
        </button>
      </form>

      <div className="buttonRow compactButtons">
        {mode !== "reset" ? (
          <button className="ghostButton" type="button" disabled={isSubmitting} onClick={() => setMode("reset")}>Forgot password? Send reset link</button>
        ) : (
          <button className="ghostButton" type="button" disabled={isSubmitting} onClick={() => setMode("login")}>Back to sign in</button>
        )}
      </div>

      <p>{message}</p>
    </div>
  );
}
