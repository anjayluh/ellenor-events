"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiPost } from "../lib/api";
import { saveSession } from "../lib/session";
import type { AuthMessage, AuthToken } from "../lib/types";

type Mode = "login" | "register" | "reset";

type ConfirmationState = {
  email: string;
  kind: "created" | "existing";
};

export function LoginForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("Sign in to continue to your Ellenor Events workspace.");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [confirmation, setConfirmation] = useState<ConfirmationState | null>(null);

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
    setConfirmation(null);
    setMessage(mode === "reset" ? "Sending your reset link..." : mode === "login" ? "Signing you in..." : "Creating your account...");
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
        setConfirmation({ email, kind: "created" });
        setMode("login");
        setPassword("");
        setMessage("Your account is almost ready.");
        return;
      }
      saveSession(result);
      setMessage(`Signed in as ${result.user.name ?? result.user.email}. Taking you to your workspace...`);
      router.replace("/");
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "We could not complete that step. Please check your details and try again.";
      if (mode === "register" && errorMessage.toLowerCase().includes("already exists")) {
        setConfirmation({ email, kind: "existing" });
        setMode("login");
        setPassword("");
        setMessage("This email already has an Ellenor Events account.");
      } else {
        setMessage(errorMessage);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function selectMode(nextMode: Mode) {
    setMode(nextMode);
    setConfirmation(null);
    setMessage(
      nextMode === "login"
        ? "Sign in to continue to your Ellenor Events workspace."
        : nextMode === "register"
          ? "Create your account in a few simple steps."
          : "We will help you get back into your account safely."
    );
    setTouched({});
  }

  const formGuidance = mode === "register"
    ? "Enter your name, email, and a password with at least 8 characters to continue."
    : mode === "reset"
      ? "Enter the email address you used to create your account."
      : "Enter your email and password to continue.";

  return (
    <div className="panel authPanel">
      <div className="segmentedControl" aria-label="Account access options" role="tablist">
        <button aria-selected={mode === "login"} className={mode === "login" ? "active" : ""} role="tab" type="button" disabled={isSubmitting} onClick={() => selectMode("login")}>Sign in</button>
        <button aria-selected={mode === "register"} className={mode === "register" ? "active" : ""} role="tab" type="button" disabled={isSubmitting} onClick={() => selectMode("register")}>Create account</button>
        <button aria-selected={mode === "reset"} className={mode === "reset" ? "active" : ""} role="tab" type="button" disabled={isSubmitting} onClick={() => selectMode("reset")}>Reset password</button>
      </div>

      <form className="stack" onSubmit={submit}>
        {mode === "register" ? (
          <label className="formField">
            Display name
            <input id="display-name" value={name} onBlur={() => setTouched((current) => ({ ...current, name: true }))} onChange={(event) => setName(event.target.value)} placeholder="Your full name" autoComplete="name" aria-describedby="display-name-help" aria-invalid={Boolean(nameError)} />
            <span className="helperText" id="display-name-help">At least 2 characters, so family and committee members can recognize you.</span>
            {touched.name && nameError ? <span className="errorText">{nameError}</span> : null}
          </label>
        ) : null}
        <label className="formField">
          Email
          <input id="auth-email" value={email} onBlur={() => setTouched((current) => ({ ...current, email: true }))} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" type="email" autoComplete="email" aria-describedby="auth-email-help" aria-invalid={Boolean(emailError)} />
          <span className="helperText" id="auth-email-help">Use the email connected to your Ellenor Events account or invitation.</span>
            {touched.email && emailError ? <span className="errorText">{emailError}</span> : null}
          </label>
        {mode === "reset" ? (
          <span className="helperText">We will email a secure reset link. Open it to choose a new password.</span>
        ) : (
          <label className="formField">
            Password
            <input id="auth-password" value={password} onBlur={() => setTouched((current) => ({ ...current, password: true }))} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} aria-describedby="auth-password-help" aria-invalid={Boolean(passwordError)} />
            <span className="helperText" id="auth-password-help">{mode === "register" ? "Use at least 8 characters. Keep it somewhere safe." : "Use the password you created for Ellenor Events."}</span>
            {touched.password && passwordError ? <span className="errorText">{passwordError}</span> : null}
          </label>
        )}
        <p className="authFormGuidance" aria-live="polite">{formGuidance}</p>
        <button className="primaryButton" disabled={!isValid || isSubmitting} type="submit">
          {isSubmitting ? (mode === "reset" ? "Sending..." : mode === "login" ? "Signing in..." : "Creating...") : (mode === "reset" ? "Send reset link" : mode === "login" ? "Sign in" : "Create account")}
        </button>
      </form>

      {confirmation ? (
        <section className="confirmationCard" aria-live="polite">
          {confirmation.kind === "created" ? (
            <>
              <p className="eyebrow">One last step</p>
              <h2>Check your email to confirm your account.</h2>
              <p>We sent a confirmation link to <strong>{confirmation.email}</strong>.</p>
              <ol>
                <li>Open the email you used to sign up.</li>
                <li>Select the confirmation link inside it.</li>
                <li>Return here and sign in with your email and password.</li>
              </ol>
              <p className="helperText">If you do not see it soon, check your spam or junk folder.</p>
            </>
          ) : (
            <>
              <p className="eyebrow">Account found</p>
              <h2>This email already has an account.</h2>
              <p>Choose <strong>Sign in</strong> below. If the account is confirmed, you can continue immediately.</p>
              <p>If it is not confirmed yet, check <strong>{confirmation.email}</strong> for the confirmation link, open it, then return here and sign in.</p>
            </>
          )}
          <button className="secondaryButton light" type="button" onClick={() => selectMode("login")}>Return to sign in</button>
        </section>
      ) : null}

      <div className="buttonRow compactButtons">
        {mode !== "reset" ? (
          <button className="ghostButton" type="button" disabled={isSubmitting} onClick={() => setMode("reset")}>Forgot password? Send reset link</button>
        ) : (
          <button className="ghostButton" type="button" disabled={isSubmitting} onClick={() => setMode("login")}>Back to sign in</button>
        )}
      </div>

      <p className="authMessage" aria-live="polite">{message}</p>
    </div>
  );
}
