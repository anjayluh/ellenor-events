"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "../lib/api";
import { StateBlock } from "./StateBlock";

type AdminUser = { id: string; name?: string | null; email?: string | null; phone?: string | null; created_at: string };
type Staff = { id: string; user_id: string; email?: string | null; name?: string | null; role: string; permissions: string[]; status: string };
type AuditLog = { id: string; actor_user_id?: string | null; project_id?: string | null; action: string; metadata: Record<string, unknown>; created_at: string };

const permissions = [
  "admin.users.view",
  "admin.users.manage",
  "admin.logs.view",
  "admin.permissions.manage",
  "admin.projects.view",
  "admin.projects.manage",
  "admin.vendors.view",
  "admin.vendors.manage"
];

const permissionLabels: Record<string, string> = {
  "admin.users.view": "View users",
  "admin.users.manage": "Manage users",
  "admin.logs.view": "View activity logs",
  "admin.permissions.manage": "Manage admin access",
  "admin.projects.view": "View events",
  "admin.projects.manage": "Manage events",
  "admin.vendors.view": "View vendors",
  "admin.vendors.manage": "Manage vendors"
};

export function AdminClientPage() {
  const [me, setMe] = useState<Staff | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("SUPPORT_AGENT");
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>(["admin.users.view"]);
  const [notice, setNotice] = useState("Ellenor Events admins can manage users, team access, and activity logs.");
  const [processing, setProcessing] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function loadAdmin() {
    const current = await apiGet<Staff>("/admin/me");
    setMe(current);
    const requests: Array<Promise<unknown>> = [];
    if (current.permissions.includes("admin.users.view")) requests.push(apiGet<AdminUser[]>("/admin/users").then(setUsers));
    if (current.permissions.includes("admin.permissions.manage")) requests.push(apiGet<Staff[]>("/admin/staff").then(setStaff));
    if (current.permissions.includes("admin.logs.view")) requests.push(apiGet<AuditLog[]>("/admin/logs").then(setLogs));
    await Promise.all(requests);
  }

  useEffect(() => {
    void loadAdmin().catch((error) => setNotice(error instanceof Error ? error.message : "Admin access required.")).finally(() => setLoaded(true));
  }, []);

  const emailError = email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? "Enter a valid email address." : "";
  const canSubmit = Boolean(email && !emailError && role && selectedPermissions.length && !processing && me?.permissions.includes("admin.permissions.manage"));

  function togglePermission(permission: string) {
    setSelectedPermissions((current) => current.includes(permission) ? current.filter((item) => item !== permission) : [...current, permission].sort());
  }

  async function grantStaff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setProcessing("grant");
    setNotice("Saving admin permissions...");
    try {
      await apiPost<Staff, { email: string; role: string; permissions: string[]; status: string }>("/admin/staff", {
        email: email.trim().toLowerCase(),
        role,
        permissions: selectedPermissions,
        status: "active"
      });
      setEmail("");
      setNotice("Admin permissions saved.");
      await loadAdmin();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not save admin permissions.");
    } finally {
      setProcessing(null);
    }
  }

  async function revoke(userId: string) {
    if (processing || !window.confirm("Remove platform admin access for this user?")) return;
    setProcessing(`revoke-${userId}`);
    try {
      await apiDelete<{ status: string }>(`/admin/staff/${userId}`);
      setNotice("Admin access removed.");
      await loadAdmin();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not remove admin access.");
    } finally {
      setProcessing(null);
    }
  }

  if (!loaded) return <StateBlock title="Loading admin" message="Checking your Ellenor Events admin access." />;
  if (!me) return <StateBlock title="Admin access required" message={notice} />;

  return (
    <section className="stack">
      <article className="hero compact">
        <p className="eyebrow">Ellenor Admin</p>
        <h1>Platform operations</h1>
        <p>You are signed in as {me.email ?? me.user_id}. Role: {me.role.replaceAll("_", " ")}.</p>
      </article>
      <section className="grid twoColumns">
        <article className="panel actionPanel">
          <p className="eyebrow">Permissions</p>
          <h2>Add or update admin</h2>
          <form className="stack" onSubmit={grantStaff}>
            <label className="formField">Admin email<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" placeholder="ops@example.com" aria-invalid={Boolean(emailError)} /><span className="helperText">Required. This user gets Ellenor Events admin access only.</span>{emailError ? <span className="errorText">{emailError}</span> : null}</label>
            <label className="formField">Role<select value={role} onChange={(event) => setRole(event.target.value)}><option value="PLATFORM_ADMIN">Platform admin</option><option value="OPERATIONS_MANAGER">Operations manager</option><option value="SUPPORT_AGENT">Support agent</option><option value="STAFF_VIEWER">Staff viewer</option></select></label>
            <div className="permissionGrid">
              {permissions.map((permission) => <label key={permission}><input checked={selectedPermissions.includes(permission)} onChange={() => togglePermission(permission)} type="checkbox" />{permissionLabels[permission]}</label>)}
            </div>
            <button className="primaryButton" data-icon="✓" disabled={!canSubmit} type="submit">{processing === "grant" ? "Saving..." : "Save admin permissions"}</button>
          </form>
          <p>{notice}</p>
        </article>
        <article className="panel tablePanel">
          <p className="eyebrow">Staff</p>
          <h2>Platform admins</h2>
          <div className="tableScroller"><table className="dataTable"><thead><tr><th>User</th><th>Role</th><th>Permissions</th><th>Actions</th></tr></thead><tbody>{staff.map((member) => <tr key={member.id}><td><strong>{member.email ?? member.user_id}</strong><small>{member.status}</small></td><td>{member.role}</td><td>{member.permissions.map((permission) => permissionLabels[permission] ?? permission).join(", ") || "Full super admin access"}</td><td><button className="ghostButton danger" data-icon="−" disabled={member.role === "SUPER_ADMIN" || Boolean(processing)} type="button" onClick={() => void revoke(member.user_id)}>{processing === `revoke-${member.user_id}` ? "Removing..." : "Remove"}</button></td></tr>)}</tbody></table></div>
        </article>
      </section>
      <section className="grid twoColumns">
        <article className="panel tablePanel"><p className="eyebrow">Users</p><h2>Recent users</h2><div className="tableScroller"><table className="dataTable"><thead><tr><th>Name</th><th>Email</th><th>Phone</th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td>{user.name ?? "No name"}</td><td>{user.email ?? "No email"}</td><td>{user.phone ?? "No phone"}</td></tr>)}</tbody></table></div></article>
        <article className="panel tablePanel"><p className="eyebrow">Audit Logs</p><h2>Recent actions</h2><div className="tableScroller"><table className="dataTable"><thead><tr><th>Action</th><th>Project</th><th>When</th></tr></thead><tbody>{logs.map((log) => <tr key={log.id}><td><strong>{log.action}</strong><small>{JSON.stringify(log.metadata)}</small></td><td>{log.project_id ?? "Platform"}</td><td>{new Date(log.created_at).toLocaleString()}</td></tr>)}</tbody></table></div></article>
      </section>
    </section>
  );
}
