"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiPost } from "../lib/api";
import type { AuthMessage } from "../lib/types";

function readRecoveryToken() {
  if (typeof window === "undefined") return "";
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const queryParams = new URLSearchParams(window.location.search);
  return hashParams.get("access_token") ?? queryParams.get("access_token") ?? "";
}

export function ResetPasswordForm() {
  const [accessToken, setAccessToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("Open the reset link from your email, then choose a new password.");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const token = readRecoveryToken();
    setAccessToken(token);
    if (token) setMessage("Reset link confirmed. Choose a new password.");
  }, []);

  const passwordError = password && password.length < 8 ? "Password must be at least 8 characters." : "";
  const confirmError = confirmPassword && password !== confirmPassword ? "Passwords must match." : "";
  const canSubmit = useMemo(() => Boolean(accessToken) && password.length >= 8 && password === confirmPassword && !passwordError && !confirmError, [accessToken, password, confirmPassword, passwordError, confirmError]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || isSubmitting) return;
    setIsSubmitting(true);
    setMessage("Updating your password...");
    try {
      const result = await apiPost<AuthMessage, { access_token: string; password: string }>("/auth/password-reset/confirm", { access_token: accessToken, password });
      setMessage(result.message);
      window.history.replaceState(null, "", "/reset-password");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Password could not be updated. Request a new reset link.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="panel authPanel">
      {!accessToken ? <p className="errorText">This reset link is incomplete or expired. Request a new password reset email from the login page.</p> : null}
      <form className="stack" onSubmit={submit}>
        <label className="formField">
          New password
          <input value={password} onBlur={() => setTouched((current) => ({ ...current, password: true }))} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" type="password" autoComplete="new-password" aria-invalid={Boolean(passwordError)} />
          <span className="helperText">Minimum 8 characters.</span>
          {touched.password && passwordError ? <span className="errorText">{passwordError}</span> : null}
        </label>
        <label className="formField">
          Confirm password
          <input value={confirmPassword} onBlur={() => setTouched((current) => ({ ...current, confirmPassword: true }))} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Repeat the new password" type="password" autoComplete="new-password" aria-invalid={Boolean(confirmError)} />
          {touched.confirmPassword && confirmError ? <span className="errorText">{confirmError}</span> : null}
        </label>
        <button className="primaryButton" disabled={!canSubmit || isSubmitting} type="submit">{isSubmitting ? "Updating..." : "Update password"}</button>
      </form>
      <p>{message}</p>
      <div className="buttonRow compactButtons">
        <Link className="ghostButton" href="/login">Back to sign in</Link>
      </div>
    </div>
  );
}
