"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../lib/api";
import type { Project } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader, EventWorkspaceGuard } from "./EventWorkspaceGuard";

type GuestInvite = {
  id: string;
  project_id: string;
  guest_name: string;
  email?: string | null;
  phone?: string | null;
  invitation_card_url?: string | null;
  token: string;
  status: string;
  attendance_status: string;
  sent_count: number;
  last_sent_at?: string | null;
  responded_at?: string | null;
  notes?: string | null;
};

type GuestSummary = { total: number; sent: number; accepted: number; declined: number; pending: number; rejected: number };
type GuestForm = { guest_name: string; email: string; phone: string; invitation_card_url: string; notes: string };
const emptyForm: GuestForm = { guest_name: "", email: "", phone: "", invitation_card_url: "", notes: "" };

function canManage(project?: Project | null) {
  return Boolean(project?.role === "OWNER" || project?.role === "PARTNER" || project?.role === "COMMITTEE_CHAIR" || project?.permissions?.includes("guest_invites.manage"));
}

export function GuestInvitesClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [invites, setInvites] = useState<GuestInvite[]>([]);
  const [summary, setSummary] = useState<GuestSummary | null>(null);
  const [form, setForm] = useState<GuestForm>(emptyForm);
  const [notice, setNotice] = useState("Guest invites are event attendance records, separate from committee access.");
  const [processing, setProcessing] = useState<string | null>(null);

  async function loadGuests(activeProject: Project) {
    const [nextInvites, nextSummary] = await Promise.all([
      apiGet<GuestInvite[]>(`/projects/${activeProject.id}/guest-invites`),
      apiGet<GuestSummary>(`/projects/${activeProject.id}/guest-invites/summary`)
    ]);
    setInvites(nextInvites);
    setSummary(nextSummary);
  }

  useEffect(() => {
    if (!project || !canManage(project)) {
      setInvites([]);
      setSummary(null);
      return;
    }
    void loadGuests(project).catch(() => setInvites([]));
  }, [project]);

  const nameError = form.guest_name && form.guest_name.trim().length < 2 ? "Guest name must be at least 2 characters." : "";
  const emailError = form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) ? "Enter a valid email address." : "";
  const contactError = !form.email.trim() && !form.phone.trim() ? "Add an email or phone number." : "";
  const canSubmit = Boolean(project && canManage(project) && form.guest_name.trim().length >= 2 && !emailError && !contactError && !processing);

  async function createGuest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmit) return;
    setProcessing("create");
    setNotice("Creating guest invite...");
    try {
      await apiPost<GuestInvite, Record<string, string | null>>(`/projects/${project.id}/guest-invites`, {
        guest_name: form.guest_name.trim(),
        email: form.email.trim().toLowerCase() || null,
        phone: form.phone.trim() || null,
        invitation_card_url: form.invitation_card_url.trim() || null,
        notes: form.notes.trim() || null
      });
      setForm(emptyForm);
      setNotice("Guest invite created. Use Send email to prepare the notification with the card link.");
      await loadGuests(project);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not create guest invite.");
    } finally {
      setProcessing(null);
    }
  }

  async function sendGuest(inviteId: string) {
    if (!project || processing) return;
    setProcessing(`send-${inviteId}`);
    setNotice("Preparing guest invitation email...");
    try {
      await apiPost<GuestInvite, Record<string, never>>(`/projects/${project.id}/guest-invites/${inviteId}/send`, {});
      setNotice("Guest invitation prepared for email delivery.");
      await loadGuests(project);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not send guest invite.");
    } finally {
      setProcessing(null);
    }
  }

  async function updateAttendance(inviteId: string, attendance_status: string) {
    if (!project || processing) return;
    setProcessing(`status-${inviteId}`);
    try {
      await apiPatch<GuestInvite, { attendance_status: string }>(`/projects/${project.id}/guest-invites/${inviteId}`, { attendance_status });
      setNotice("Attendance status updated.");
      await loadGuests(project);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not update attendance.");
    } finally {
      setProcessing(null);
    }
  }

  if (state !== "ready") return <EventWorkspaceGuard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;

  return (
    <>
      <EventScopedHeader projects={projects} project={project} onSelect={selectProject} />
      <section className="grid fourColumns">
        <article className="metric"><span>Total guests</span><strong>{summary?.total ?? 0}</strong></article>
        <article className="metric"><span>Sent</span><strong>{summary?.sent ?? 0}</strong></article>
        <article className="metric"><span>Accepted</span><strong>{summary?.accepted ?? 0}</strong></article>
        <article className="metric"><span>Declined/Rejected</span><strong>{(summary?.declined ?? 0) + (summary?.rejected ?? 0)}</strong></article>
      </section>
      <section className="grid twoColumns">
        <article className="panel actionPanel">
          <p className="eyebrow">Guest RSVPs</p>
          <h2>Invite event guests</h2>
          {canManage(project) ? (
            <form className="stack" onSubmit={createGuest}>
              <label className="formField">Guest name<input value={form.guest_name} onChange={(event) => setForm((current) => ({ ...current, guest_name: event.target.value }))} placeholder="Auntie Rose" aria-invalid={Boolean(nameError)} /><span className="helperText">Required. At least 2 characters.</span>{nameError ? <span className="errorText">{nameError}</span> : null}</label>
              <label className="formField">Email<input value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} placeholder="guest@example.com" type="email" aria-invalid={Boolean(emailError || contactError)} /><span className="helperText">Use email for free invitation notifications where possible.</span>{emailError || contactError ? <span className="errorText">{emailError || contactError}</span> : null}</label>
              <label className="formField">Phone<input value={form.phone} onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))} placeholder="+256..." /></label>
              <label className="formField">Invitation card URL<input value={form.invitation_card_url} onChange={(event) => setForm((current) => ({ ...current, invitation_card_url: event.target.value }))} placeholder="https://.../card.png" /><span className="helperText">Upload the card to free storage and paste the public link here.</span></label>
              <label className="formField">Notes<input value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Bride family VIP table" /></label>
              <button className="primaryButton" data-icon="+" disabled={!canSubmit} type="submit">{processing === "create" ? "Creating..." : "Create guest invite"}</button>
            </form>
          ) : <p>Your role can view the event but cannot manage guest invitations.</p>}
          <p>{notice}</p>
        </article>
        <section className="stack">
          {canManage(project) && invites.length ? invites.map((invite) => (
            <article className="panel resourceCard" key={invite.id}>
              <p className="eyebrow">{invite.status} · {invite.attendance_status}</p>
              <h2>{invite.guest_name}</h2>
              <p>{invite.email ?? invite.phone}</p>
              <p>Sent {invite.sent_count} time(s). Last sent: {invite.last_sent_at ?? "Not yet"}</p>
              {invite.invitation_card_url ? <a className="ghostButton" data-icon="↗" href={invite.invitation_card_url} rel="noreferrer" target="_blank">View card</a> : null}
              <p className="tokenNote">/guest-invite/{invite.token}</p>
              <div className="buttonRow">
                <button className="ghostButton" data-icon="✉" disabled={Boolean(processing)} type="button" onClick={() => void sendGuest(invite.id)}>{processing === `send-${invite.id}` ? "Sending..." : "Send email"}</button>
                <select aria-label="Attendance status" disabled={Boolean(processing)} value={invite.attendance_status} onChange={(event) => void updateAttendance(invite.id, event.target.value)}>
                  <option value="pending">Pending</option>
                  <option value="accepted">Accepted</option>
                  <option value="confirmed">Confirmed by manager</option>
                  <option value="declined">Declined</option>
                  <option value="rejected">Rejected</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </article>
          )) : <article className="panel"><h2>No guest invites yet</h2><p>{canManage(project) ? "Create the first guest invite and attach the invitation card link." : "Guest RSVP management is limited to event admins."}</p></article>}
        </section>
      </section>
    </>
  );
}
