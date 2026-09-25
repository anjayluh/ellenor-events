"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import { formatDate } from "../lib/customer-display";
import type { Project } from "../lib/types";
import { useActiveProject } from "../lib/useActiveProject";
import { EventScopedHeader, EventWorkspaceGuard } from "./EventWorkspaceGuard";
import { StateBlock } from "./StateBlock";

type TaskStatus = "TODO" | "IN_PROGRESS" | "DONE";
type TaskPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";
type TaskCategory = "GENERAL" | "PROGRAM" | "FINANCE" | "GUESTS" | "VENDORS" | "LOGISTICS" | "VENUE" | "DECOR" | "COMMUNICATION" | "FAMILY" | "COMMITTEE";
type Task = {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  assigned_to?: string | null;
  assignee_name?: string | null;
  assignee_email?: string | null;
  created_by_user_id?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  category: TaskCategory;
  due_date?: string | null;
  completed_at?: string | null;
  is_overdue: boolean;
  is_due_soon: boolean;
};
type TaskSummary = { project_id: string; total: number; todo: number; in_progress: number; completed: number; overdue: number; due_soon: number; completion_percentage: number; my_tasks: number };
type TaskAssignee = { user_id: string; name?: string | null; email?: string | null; role: string };
type TaskForm = { title: string; description: string; status: TaskStatus; priority: TaskPriority; category: TaskCategory; assigned_to: string; due_date: string };
type TaskFilters = { search: string; status: string; priority: string; category: string; assignee: string; preset: string };
type TaskPayload = { title: string; description: string | null; status: TaskStatus; priority: TaskPriority; category: TaskCategory; assigned_to: string | null; due_date: string | null };

const emptyForm: TaskForm = { title: "", description: "", status: "TODO", priority: "MEDIUM", category: "GENERAL", assigned_to: "", due_date: "" };
const emptyFilters: TaskFilters = { search: "", status: "", priority: "", category: "", assignee: "", preset: "all" };
const statuses: Array<{ value: TaskStatus; label: string }> = [{ value: "TODO", label: "To Do" }, { value: "IN_PROGRESS", label: "In Progress" }, { value: "DONE", label: "Completed" }];
const priorities: Array<{ value: TaskPriority; label: string }> = [{ value: "LOW", label: "Low" }, { value: "MEDIUM", label: "Medium" }, { value: "HIGH", label: "High" }, { value: "URGENT", label: "Urgent" }];
const categories: Array<{ value: TaskCategory; label: string }> = [
  { value: "GENERAL", label: "General" },
  { value: "PROGRAM", label: "Program" },
  { value: "FINANCE", label: "Finance" },
  { value: "GUESTS", label: "Guests" },
  { value: "VENDORS", label: "Vendors" },
  { value: "LOGISTICS", label: "Logistics" },
  { value: "VENUE", label: "Venue" },
  { value: "DECOR", label: "Decor" },
  { value: "COMMUNICATION", label: "Communication" },
  { value: "FAMILY", label: "Family" },
  { value: "COMMITTEE", label: "Committee" }
];
const presets = [
  { value: "all", label: "All" },
  { value: "my", label: "My Tasks" },
  { value: "todo", label: "To Do" },
  { value: "in_progress", label: "In Progress" },
  { value: "done", label: "Completed" },
  { value: "overdue", label: "Overdue" },
  { value: "due_soon", label: "Due Soon" }
];

function canManageTasks(project?: Project | null) {
  return Boolean(project?.role === "OWNER" || project?.role === "PARTNER" || project?.role === "COMMITTEE_CHAIR" || project?.role === "COMMITTEE_MEMBER" || project?.permissions?.includes("tasks.manage"));
}

function titleCase(value: string) {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function assigneeLabel(assignee: TaskAssignee) {
  return assignee.name || assignee.email || assignee.user_id.slice(0, 8);
}

function taskAssignee(task: Task) {
  return task.assignee_name || task.assignee_email || (task.assigned_to ? task.assigned_to.slice(0, 8) : "Unassigned");
}

function normalizeApiMessage(error: unknown) {
  return error instanceof Error ? error.message : "We could not complete that request.";
}

function toPayload(form: TaskForm): TaskPayload {
  return {
    title: form.title.trim(),
    description: form.description.trim() || null,
    status: form.status,
    priority: form.priority,
    category: form.category,
    assigned_to: form.assigned_to || null,
    due_date: form.due_date || null
  };
}

function formFromTask(task: Task): TaskForm {
  return {
    title: task.title,
    description: task.description ?? "",
    status: task.status,
    priority: task.priority,
    category: task.category,
    assigned_to: task.assigned_to ?? "",
    due_date: task.due_date ?? ""
  };
}

function buildQuery(filters: TaskFilters) {
  const params = new URLSearchParams();
  if (filters.search.trim()) params.set("search", filters.search.trim());
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.category) params.set("category", filters.category);
  if (filters.assignee) params.set("assignee", filters.assignee);
  if (filters.status) params.set("status", filters.status);
  if (filters.preset === "my") params.set("my_tasks", "true");
  if (filters.preset === "todo") params.set("status", "TODO");
  if (filters.preset === "in_progress") params.set("status", "IN_PROGRESS");
  if (filters.preset === "done") params.set("status", "DONE");
  if (filters.preset === "overdue") params.set("overdue", "true");
  if (filters.preset === "due_soon") params.set("due_soon", "true");
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function TasksClientPage() {
  const { projects, project, state, message, selectProject, reload } = useActiveProject();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [summary, setSummary] = useState<TaskSummary | null>(null);
  const [assignees, setAssignees] = useState<TaskAssignee[]>([]);
  const [form, setForm] = useState<TaskForm>(emptyForm);
  const [editForm, setEditForm] = useState<TaskForm>(emptyForm);
  const [filters, setFilters] = useState<TaskFilters>(emptyFilters);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [notice, setNotice] = useState("Create clear responsibilities for the event team without adding noise.");
  const [processing, setProcessing] = useState<string | null>(null);

  const loadTasks = useCallback(async (activeProject: Project, nextFilters: TaskFilters) => {
    const [nextTasks, nextSummary, nextAssignees] = await Promise.all([
      apiGet<Task[]>(`/projects/${activeProject.id}/tasks${buildQuery(nextFilters)}`),
      apiGet<TaskSummary>(`/projects/${activeProject.id}/tasks/summary`),
      apiGet<TaskAssignee[]>(`/projects/${activeProject.id}/tasks/assignees`)
    ]);
    setTasks(nextTasks);
    setSummary(nextSummary);
    setAssignees(nextAssignees);
  }, []);

  useEffect(() => {
    if (!project) return;
    void loadTasks(project, filters).catch((error) => {
      setTasks([]);
      setSummary(null);
      setNotice(normalizeApiMessage(error));
    });
  }, [project, filters, loadTasks]);

  const titleError = form.title && form.title.trim().length < 3 ? "Task title must be at least 3 characters." : "";
  const canManage = canManageTasks(project);
  const canSubmit = Boolean(project && canManage && form.title.trim().length >= 3 && !titleError && !processing);

  async function createTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!project || !canSubmit) return;
    setProcessing("create");
    setNotice("Creating task...");
    try {
      await apiPost<Task, TaskPayload>(`/projects/${project.id}/tasks`, toPayload(form));
      setForm(emptyForm);
      setNotice("Task created. Keep statuses updated as plans move forward.");
      await loadTasks(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  function startEdit(task: Task) {
    setEditingTaskId(task.id);
    setEditForm(formFromTask(task));
  }

  async function updateTask(taskId: string, payload?: Partial<TaskPayload>) {
    if (!project || processing) return;
    setProcessing(`update-${taskId}`);
    try {
      await apiPatch<Task, Partial<TaskPayload>>(`/projects/${project.id}/tasks/${taskId}`, payload ?? toPayload(editForm));
      setEditingTaskId(null);
      setNotice("Task updated.");
      await loadTasks(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function deleteTask(taskId: string) {
    if (!project || processing || !window.confirm("Delete this task from the event plan?")) return;
    setProcessing(`delete-${taskId}`);
    try {
      await apiDelete<{ status: string }>(`/projects/${project.id}/tasks/${taskId}`);
      setNotice("Task deleted.");
      await loadTasks(project, filters);
    } catch (error) {
      setNotice(normalizeApiMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  const completedWidth = `${summary?.completion_percentage ?? 0}%`;
  if (state !== "ready") return <EventWorkspaceGuard state={state} message={message} projects={projects} onSelect={selectProject} onCreated={() => void reload()} />;

  return (
    <>
      <EventScopedHeader projects={projects} project={project} onSelect={selectProject} />
      <section className="grid fourColumns">
        <article className="metric"><span>Total tasks</span><strong>{summary?.total ?? 0}</strong><p>{summary?.my_tasks ?? 0} assigned to you</p></article>
        <article className="metric"><span>To do</span><strong>{summary?.todo ?? 0}</strong><p>{summary?.in_progress ?? 0} in progress</p></article>
        <article className="metric"><span>Completed</span><strong>{summary?.completed ?? 0}</strong><p>{summary?.completion_percentage ?? 0}% complete</p></article>
        <article className="metric"><span>Needs attention</span><strong>{summary?.overdue ?? 0}</strong><p>{summary?.due_soon ?? 0} due in the next 7 days</p></article>
      </section>

      <section className="panel resourceCard">
        <div className="cardTitleRow"><div><p className="eyebrow">Planning progress</p><h2>Task completion</h2></div><span className="badge softBadge">Live event data</span></div>
        <div className="progressTrack" aria-label="Task completion"><div className="progressFill" style={{ width: completedWidth }} /></div>
        <p>{summary?.completion_percentage ?? 0}% complete · {summary?.overdue ?? 0} overdue · {summary?.due_soon ?? 0} due soon</p>
      </section>

      <section className="grid twoColumns">
        <article className="panel actionPanel">
          <p className="eyebrow">Tasks</p>
          <h2>Create task</h2>
          {canManage ? (
            <form className="stack" onSubmit={createTask}>
              <label className="formField">Title<input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="Confirm reception programme" aria-invalid={Boolean(titleError)} />{titleError ? <span className="errorText">{titleError}</span> : <span className="helperText">Make it specific enough for someone to act.</span>}</label>
              <label className="formField">Description<input value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="Optional context, family contact, or expected outcome" /></label>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Category<select value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value as TaskCategory }))}>{categories.map((category) => <option value={category.value} key={category.value}>{category.label}</option>)}</select></label>
                <label className="formField">Priority<select value={form.priority} onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value as TaskPriority }))}>{priorities.map((priority) => <option value={priority.value} key={priority.value}>{priority.label}</option>)}</select></label>
              </div>
              <div className="grid twoColumns compactGrid">
                <label className="formField">Assignee<select value={form.assigned_to} onChange={(event) => setForm((current) => ({ ...current, assigned_to: event.target.value }))}><option value="">Unassigned</option>{assignees.map((assignee) => <option value={assignee.user_id} key={assignee.user_id}>{assigneeLabel(assignee)} · {titleCase(assignee.role)}</option>)}</select></label>
                <label className="formField">Due date<input type="date" value={form.due_date} onChange={(event) => setForm((current) => ({ ...current, due_date: event.target.value }))} /></label>
              </div>
              <button className="primaryButton" data-icon="+" disabled={!canSubmit} type="submit">{processing === "create" ? "Creating..." : "Create task"}</button>
            </form>
          ) : <p>You can view tasks for this event, but creating or assigning work is limited to event coordinators.</p>}
          <p>{notice}</p>
        </article>

        <article className="panel resourceCard">
          <p className="eyebrow">Filters</p>
          <h2>Focus the plan</h2>
          <div className="stack">
            <div className="segmentedControl">{presets.map((preset) => <button className={filters.preset === preset.value ? "active" : ""} key={preset.value} type="button" onClick={() => setFilters((current) => ({ ...current, preset: preset.value, status: "" }))}>{preset.label}</button>)}</div>
            <label className="formField">Search<input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Task title or description" /></label>
            <div className="grid twoColumns compactGrid">
              <label className="formField">Priority<select value={filters.priority} onChange={(event) => setFilters((current) => ({ ...current, priority: event.target.value }))}><option value="">All priorities</option>{priorities.map((priority) => <option value={priority.value} key={priority.value}>{priority.label}</option>)}</select></label>
              <label className="formField">Category<select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}><option value="">All categories</option>{categories.map((category) => <option value={category.value} key={category.value}>{category.label}</option>)}</select></label>
            </div>
            <label className="formField">Assignee<select value={filters.assignee} onChange={(event) => setFilters((current) => ({ ...current, assignee: event.target.value }))}><option value="">Anyone</option>{assignees.map((assignee) => <option value={assignee.user_id} key={assignee.user_id}>{assigneeLabel(assignee)}</option>)}</select></label>
            <button className="ghostButton" data-icon="×" type="button" onClick={() => setFilters(emptyFilters)}>Clear filters</button>
          </div>
        </article>
      </section>

      <section className="panel tablePanel">
        <div className="sectionHeader"><div><p className="eyebrow">Event tasks</p><h2>Responsibilities and next steps</h2></div><span className="badge softBadge">{tasks.length} shown</span></div>
        {tasks.length ? (
          <div className="tableScroller">
            <table className="dataTable">
              <thead><tr><th>Task</th><th>Planning</th><th>Assignee</th><th>Due</th><th>Actions</th></tr></thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id}>
                    <td>{editingTaskId === task.id ? <div className="stack"><input value={editForm.title} onChange={(event) => setEditForm((current) => ({ ...current, title: event.target.value }))} /><input value={editForm.description} onChange={(event) => setEditForm((current) => ({ ...current, description: event.target.value }))} /></div> : <><strong>{task.title}</strong>{task.description ? <small>{task.description}</small> : null}</>}</td>
                    <td>{editingTaskId === task.id ? <div className="stack"><select value={editForm.status} onChange={(event) => setEditForm((current) => ({ ...current, status: event.target.value as TaskStatus }))}>{statuses.map((status) => <option value={status.value} key={status.value}>{status.label}</option>)}</select><select value={editForm.priority} onChange={(event) => setEditForm((current) => ({ ...current, priority: event.target.value as TaskPriority }))}>{priorities.map((priority) => <option value={priority.value} key={priority.value}>{priority.label}</option>)}</select><select value={editForm.category} onChange={(event) => setEditForm((current) => ({ ...current, category: event.target.value as TaskCategory }))}>{categories.map((category) => <option value={category.value} key={category.value}>{category.label}</option>)}</select></div> : <><span className={task.status === "DONE" ? "badge successBadge" : "badge softBadge"}>{statuses.find((status) => status.value === task.status)?.label ?? titleCase(task.status)}</span><small>{titleCase(task.priority)} priority · {titleCase(task.category)}</small></>}</td>
                    <td>{editingTaskId === task.id ? <select value={editForm.assigned_to} onChange={(event) => setEditForm((current) => ({ ...current, assigned_to: event.target.value }))}><option value="">Unassigned</option>{assignees.map((assignee) => <option value={assignee.user_id} key={assignee.user_id}>{assigneeLabel(assignee)}</option>)}</select> : taskAssignee(task)}</td>
                    <td>{editingTaskId === task.id ? <input type="date" value={editForm.due_date} onChange={(event) => setEditForm((current) => ({ ...current, due_date: event.target.value }))} /> : <><strong>{task.due_date ? formatDate(task.due_date) : "No date"}</strong>{task.is_overdue ? <small className="errorText">Overdue</small> : task.is_due_soon ? <small>Due soon</small> : null}</>}</td>
                    <td><div className="buttonRow tableActions">{editingTaskId === task.id ? <><button className="primaryButton" data-icon="✓" disabled={Boolean(processing)} type="button" onClick={() => void updateTask(task.id)}>{processing === `update-${task.id}` ? "Saving..." : "Save"}</button><button className="ghostButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => setEditingTaskId(null)}>Cancel</button></> : <>{canManage ? <button className="ghostButton" data-icon="✎" disabled={Boolean(processing)} type="button" onClick={() => startEdit(task)}>Edit</button> : null}{canManage ? (task.status === "DONE" ? <button className="ghostButton" data-icon="↺" disabled={Boolean(processing)} type="button" onClick={() => void updateTask(task.id, { status: "IN_PROGRESS" })}>Reopen</button> : <button className="ghostButton" data-icon="✓" disabled={Boolean(processing)} type="button" onClick={() => void updateTask(task.id, { status: "DONE" })}>Complete</button>) : null}{canManage ? <button className="ghostButton danger" data-icon="−" disabled={Boolean(processing)} type="button" onClick={() => void deleteTask(task.id)}>{processing === `delete-${task.id}` ? "Deleting..." : "Delete"}</button> : null}</>}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
         ) : <StateBlock title={filters.search || filters.status || filters.priority || filters.category || filters.assignee || filters.preset !== "all" ? "No tasks match these filters" : "No tasks yet"} message={canManage ? "Start organising your event by creating your first task." : "Tasks will appear here once the planning team creates them."} />}
      </section>
    </>
  );
}
