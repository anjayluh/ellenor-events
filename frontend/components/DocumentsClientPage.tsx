"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiUpload } from "../lib/api";
import { formatDate } from "../lib/customer-display";
import { useActiveProject } from "../lib/useActiveProject";
import type { DocumentCategory, DocumentSummary, ProjectDocument, ProjectRole } from "../lib/types";
import { ActiveEventSwitcher } from "./ActiveEventSwitcher";
import { StateBlock } from "./StateBlock";

const categories: Array<{ value: DocumentCategory; label: string }> = [
  { value: "INVITATION", label: "Invitation" },
  { value: "CONTRACT", label: "Contract" },
  { value: "QUOTATION", label: "Quotation" },
  { value: "INVOICE", label: "Invoice" },
  { value: "RECEIPT", label: "Receipt" },
  { value: "VENUE", label: "Venue" },
  { value: "PLANNING", label: "Planning" },
  { value: "FAMILY", label: "Family" },
  { value: "COMMITTEE", label: "Committee" },
  { value: "OTHER", label: "Other" }
];

const managerRoles: ProjectRole[] = ["OWNER", "PARTNER", "COMMITTEE_CHAIR"];
type MemberOption = { user_id: string; user_name?: string | null; user_email?: string | null };

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isPreviewable(document: ProjectDocument) {
  return document.mime_type.startsWith("image/") || document.mime_type === "application/pdf";
}

export function DocumentsClientPage() {
  const { projects, project, state, message, selectProject } = useActiveProject();
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [summary, setSummary] = useState<DocumentSummary | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [uploaderId, setUploaderId] = useState("");
  const [members, setMembers] = useState<MemberOption[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadCategory, setUploadCategory] = useState<DocumentCategory>("OTHER");
  const [description, setDescription] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingDescription, setEditingDescription] = useState("");
  const [processing, setProcessing] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const canManage = Boolean(project && (managerRoles.includes(project.role ?? "FAMILY_VIEWER") || project.permissions?.includes("documents.manage")));

  const loadDocuments = useCallback(async (projectId: string) => {
    const params = new URLSearchParams({ include_archived: String(includeArchived) });
    if (search.trim()) params.set("search", search.trim());
    if (category) params.set("category", category);
    if (uploaderId) params.set("uploader_id", uploaderId);
    const [nextDocuments, nextSummary, nextMembers] = await Promise.all([
      apiGet<ProjectDocument[]>(`/projects/${projectId}/documents?${params.toString()}`),
      apiGet<DocumentSummary>(`/projects/${projectId}/documents/summary`),
      apiGet<MemberOption[]>(`/projects/${projectId}/members`)
    ]);
    setDocuments(nextDocuments);
    setSummary(nextSummary);
    setMembers(nextMembers);
  }, [category, includeArchived, search, uploaderId]);

  useEffect(() => {
    if (!project) return;
    void loadDocuments(project.id).catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : "Could not load event documents."));
  }, [project, loadDocuments]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
  }

  function uploaderLabel(userId: string) {
    const member = members.find((item) => item.user_id === userId);
    return member?.user_name || member?.user_email || "Event team member";
  }

  async function uploadDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !selectedFile || processing) return;
    setProcessing("upload");
    setError("");
    setNotice("Uploading securely to this event workspace...");
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("category", uploadCategory);
      if (description.trim()) formData.append("description", description.trim());
      await apiUpload<ProjectDocument>(`/projects/${project.id}/documents`, formData);
      setSelectedFile(null);
      setDescription("");
      const input = document.getElementById("document-file") as HTMLInputElement | null;
      if (input) input.value = "";
      setNotice("Document added to your event files.");
      await loadDocuments(project.id);
    } catch (uploadError: unknown) {
      setError(uploadError instanceof Error ? uploadError.message : "Could not upload this document.");
      setNotice("");
    } finally {
      setProcessing(null);
    }
  }

  async function openDocument(document: ProjectDocument) {
    if (!project || processing) return;
    setProcessing(`open-${document.id}`);
    setError("");
    try {
      const result = await apiGet<{ url: string }>(`/projects/${project.id}/documents/${document.id}/url`);
      window.open(result.url, "_blank", "noopener,noreferrer");
    } catch (openError: unknown) {
      setError(openError instanceof Error ? openError.message : "Could not open this document.");
    } finally {
      setProcessing(null);
    }
  }

  async function saveDescription(document: ProjectDocument) {
    if (!project || processing) return;
    setProcessing(`edit-${document.id}`);
    try {
      await apiPatch<ProjectDocument, { description: string | null }>(`/projects/${project.id}/documents/${document.id}`, { description: editingDescription.trim() || null });
      setEditingId(null);
      setNotice("Document details updated.");
      await loadDocuments(project.id);
    } catch (updateError: unknown) {
      setError(updateError instanceof Error ? updateError.message : "Could not update this document.");
    } finally {
      setProcessing(null);
    }
  }

  async function archiveDocument(document: ProjectDocument) {
    if (!project || processing || !window.confirm(`Archive ${document.original_filename}?`)) return;
    setProcessing(`archive-${document.id}`);
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/documents/${document.id}`);
      setNotice("Document archived. Its history remains available.");
      await loadDocuments(project.id);
    } catch (archiveError: unknown) {
      setError(archiveError instanceof Error ? archiveError.message : "Could not archive this document.");
    } finally {
      setProcessing(null);
    }
  }

  if (state === "anonymous") return <StateBlock title="Sign in required" message="Sign in to manage event documents." />;
  if (state === "loading") return <StateBlock title="Loading event files" message="Preparing your secure document workspace." />;
  if (state === "empty") return <StateBlock title="No event workspace yet" message="Create or join an event before adding documents." />;
  if (state === "selection_required") return <ActiveEventSwitcher projects={projects} activeProjectId={project?.id} onChange={selectProject} />;
  if (!project) return <StateBlock title="Could not load event" message={message || "Choose an event to continue."} />;

  return (
    <>
      <section className="hero compact">
        <p className="eyebrow">Event files</p>
        <div className="sectionHeaderRow"><div><h1>Documents &amp; Files</h1><p>Keep the agreements, invitations, receipts, and planning files for {project.title} together.</p></div>{canManage ? <a className="primaryButton" href="#upload-document" data-icon="+">Upload file</a> : null}</div>
      </section>

      <section className="grid fourColumns eventMetricGrid">
        <article className="metric eventMetric"><span>Active files</span><strong>{summary?.active ?? "—"}</strong><p>Available to your event team.</p></article>
        <article className="metric eventMetric"><span>Archived</span><strong>{summary?.archived ?? "—"}</strong><p>History kept safely.</p></article>
        <article className="metric eventMetric"><span>Stored</span><strong>{summary ? formatSize(summary.total_size_bytes) : "—"}</strong><p>Private event storage.</p></article>
        <article className="metric eventMetric"><span>Access</span><strong>{canManage ? "Manage" : "View"}</strong><p>Based on your event role.</p></article>
      </section>

      {canManage ? <section className="panel actionPanel" id="upload-document"><div className="sectionHeaderRow"><div><p className="eyebrow">Secure upload</p><h2>Add an event file</h2></div><span className="helperText">PDF, Word, Excel, CSV, JPG, PNG, or WEBP · up to 10 MB</span></div><form className="stack" onSubmit={uploadDocument}><div className="formGrid"><label className="formField">File<input id="document-file" type="file" accept="application/pdf,.doc,.docx,.xls,.xlsx,.csv,image/jpeg,image/png,image/webp" onChange={handleFileChange} required /></label><label className="formField">Category<select value={uploadCategory} onChange={(event) => setUploadCategory(event.target.value as DocumentCategory)}>{categories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label></div><label className="formField">Description <textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={500} placeholder="Optional context for the planning team." /></label><button className="primaryButton" type="submit" disabled={!selectedFile || Boolean(processing)}>{processing === "upload" ? "Uploading..." : "Add file"}</button>{processing === "upload" ? <progress className="uploadProgress" aria-label="Uploading document" /> : null}</form></section> : null}

      <section className="panel resourceCard"><div className="sectionHeaderRow"><div><p className="eyebrow">Event repository</p><h2>Your files</h2></div><div className="filterRow"><input aria-label="Search files" placeholder="Search files" value={search} onChange={(event) => setSearch(event.target.value)} /><select aria-label="Filter by category" value={category} onChange={(event) => setCategory(event.target.value)}><option value="">All categories</option>{categories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select><select aria-label="Filter by uploader" value={uploaderId} onChange={(event) => setUploaderId(event.target.value)}><option value="">All uploaders</option>{members.map((member) => <option key={member.user_id} value={member.user_id}>{uploaderLabel(member.user_id)}</option>)}</select><label className="checkboxField"><input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} /> Show archived</label></div></div>{error ? <p className="errorText">{error}</p> : null}{notice ? <p className="successText">{notice}</p> : null}{documents.length ? <div className="documentList">{documents.map((document) => <article className={document.is_archived ? "documentCard archived" : "documentCard"} key={document.id}><div className="documentIcon">{document.mime_type.startsWith("image/") ? "IMG" : document.mime_type === "application/pdf" ? "PDF" : "FILE"}</div><div className="documentCardBody"><div className="sectionHeaderRow"><div><h3>{document.original_filename}</h3><div className="planningAreaList"><span className="badge softBadge">{titleCase(document.category)}</span>{document.is_archived ? <span className="badge">Archived</span> : null}</div></div><span className="helperText">{formatSize(document.file_size_bytes)}</span></div><p>{document.description || "No description added."}</p><small>Added {document.created_at ? formatDate(document.created_at) : "recently"} · Uploaded by {uploaderLabel(document.uploaded_by_user_id)}</small><div className="buttonRow">{isPreviewable(document) ? <button className="ghostButton" type="button" onClick={() => void openDocument(document)} disabled={Boolean(processing)}>Open securely</button> : <button className="ghostButton" type="button" onClick={() => void openDocument(document)} disabled={Boolean(processing)}>Download securely</button>}{canManage && !document.is_archived ? <button className="ghostButton" type="button" onClick={() => { setEditingId(document.id); setEditingDescription(document.description ?? ""); }}>Edit details</button> : null}{canManage && !document.is_archived ? <button className="ghostButton danger" type="button" onClick={() => void archiveDocument(document)}>Archive</button> : null}</div>{editingId === document.id ? <div className="inlineEdit"><textarea value={editingDescription} onChange={(event) => setEditingDescription(event.target.value)} maxLength={500} /><div className="buttonRow"><button className="primaryButton" type="button" onClick={() => void saveDescription(document)}>Save</button><button className="ghostButton" type="button" onClick={() => setEditingId(null)}>Cancel</button></div></div> : null}</div></article>)}</div> : <div className="emptyState"><p className="eyebrow">A calm place for the details</p><h3>{includeArchived ? "No archived files" : "No files added yet"}</h3><p>{includeArchived ? "Archived event files will remain available here for your planning history." : "Keep invitation artwork, agreements, quotes, receipts, and planning notes together."}</p>{canManage ? <a className="primaryButton" href="#upload-document">Add your first file</a> : null}</div>}</section>
    </>
  );
}
