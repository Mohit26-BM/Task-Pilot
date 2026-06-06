let projects = [];
let users = [];
let tasks = [];
let viewMode = localStorage.getItem("taskpilot_view") || "grid";

const STATUSES = ["Pending", "In Progress", "Review", "Completed"];
const STATUS_COLORS = { "Pending": "#f59e0b", "In Progress": "#8b5cf6", "Review": "#3b82f6", "Completed": "#10b981" };
const typeIcon = { Bug: "!", Feature: "+", Improvement: "^", Documentation: "#", Research: "*" };

function statusClass(s) {
  return { "Pending": "status-pending", "In Progress": "status-progress", "Review": "status-review", "Completed": "status-completed" }[s] || "status-pending";
}
function typeClass(t) { return `type-${(t || "").toLowerCase()}`; }

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c]));
}

function scorePasswordLocal(pw) {
  return [pw.length >= 8, /[a-z]/.test(pw), /[A-Z]/.test(pw), /\d/.test(pw), /[^A-Za-z0-9]/.test(pw)].filter(Boolean).length;
}

// ===== Data loaders =====
async function loadLookups() {
  projects = await api("/projects");
  try { users = await api("/users/options"); } catch { users = []; }
  const pf = document.getElementById("projectFilter");
  if (pf && projects.length) {
    pf.innerHTML = `<option value="">All projects</option>` +
      projects.map(p => `<option value="${p.id}">${escapeHtml(p.title)}</option>`).join("");
  }
}

function fillTaskSelects(form) {
  form.project_id.innerHTML = projects.map(p => `<option value="${p.id}">${escapeHtml(p.title)}</option>`).join("");
  form.assigned_to.innerHTML = `<option value="">Unassigned</option>` +
    users.map(u => `<option value="${u.id}">${escapeHtml(u.name)}</option>`).join("");
}

// ===== Task list card =====
function taskCard(task) {
  const admin = store.user?.role === "Admin";
  return `
    <article class="task-card priority-${task.priority}">
      <div class="card-meta">
        <span class="pill ${typeClass(task.task_type)}">${typeIcon[task.task_type] || "-"} ${task.task_type}</span>
        <span class="pill ${statusClass(task.status)}">${task.status}</span>
      </div>
      <h3>${escapeHtml(task.title)}</h3>
      <p class="muted">${escapeHtml(task.description || "No description")}</p>
      <div class="card-meta">
        <span class="muted">${escapeHtml(task.project_title || "")}</span>
        <span class="pill">${task.priority}</span>
      </div>
      <div class="card-meta">
        <span class="${task.is_overdue ? "pill type-bug" : "muted"}">${task.is_overdue ? "Overdue · " : ""}${formatDate(task.due_date)}</span>
        <span class="muted">${escapeHtml(task.assignee_name)}</span>
      </div>
      <div class="task-actions">
        <select data-status="${task.id}">
          ${STATUSES.map(s => `<option ${s === task.status ? "selected" : ""}>${s}</option>`).join("")}
        </select>
        ${admin ? `<button class="ghost-btn" data-edit-task="${task.id}">Edit</button><button class="danger-btn" data-delete-task="${task.id}">Delete</button>` : ""}
      </div>
    </article>`;
}

// ===== Kanban card =====
function kanbanCard(task) {
  const admin = store.user?.role === "Admin";
  const initials = task.assignee_name !== "Unassigned" ? escapeHtml(task.assignee_name[0].toUpperCase()) : "?";
  return `
    <div class="kanban-card priority-${task.priority}" data-id="${task.id}">
      <span class="pill ${typeClass(task.task_type)}" style="font-size:10px;padding:2px 7px;">${escapeHtml(task.task_type)}</span>
      <p class="kanban-card-title">${escapeHtml(task.title)}</p>
      <div class="kanban-card-meta">
        <span class="${task.is_overdue ? "overdue-badge" : "muted-sm"}">${task.is_overdue ? "⚠ Overdue" : formatDate(task.due_date)}</span>
        <span class="avatar avatar-sm" title="${escapeHtml(task.assignee_name)}">${initials}</span>
      </div>
      ${admin ? `
      <div class="kanban-card-actions">
        <button class="icon-btn icon-btn-sm" data-edit-task="${task.id}" title="Edit">✎</button>
        <button class="icon-btn icon-btn-sm danger" data-delete-task="${task.id}" title="Delete">✕</button>
      </div>` : ""}
    </div>`;
}

// ===== Render kanban board =====
function renderKanban(taskList) {
  const board = document.getElementById("kanbanBoard");
  if (!board) return;

  const grouped = Object.fromEntries(STATUSES.map(s => [s, []]));
  taskList.forEach(t => { if (grouped[t.status] !== undefined) grouped[t.status].push(t); });

  board.innerHTML = STATUSES.map(status => `
    <div class="kanban-col">
      <div class="kanban-col-head">
        <div class="kanban-col-label">
          <span class="kanban-dot" style="background:${STATUS_COLORS[status]}"></span>
          <span class="kanban-col-title">${status}</span>
        </div>
        <span class="kanban-col-count" id="kc-${status.replace(/ /g, "-")}">${grouped[status].length}</span>
      </div>
      <div class="kanban-cards" data-status="${status}">
        ${grouped[status].map(kanbanCard).join("")}
      </div>
    </div>`).join("");

  if (typeof Sortable !== "undefined") {
    board.querySelectorAll(".kanban-cards").forEach(col => {
      Sortable.create(col, {
        group: "kanban",
        animation: 160,
        ghostClass: "sortable-ghost",
        chosenClass: "sortable-chosen",
        onEnd: async (evt) => {
          const taskId = Number(evt.item.dataset.id);
          const newStatus = evt.to.dataset.status;
          if (evt.from === evt.to && evt.oldIndex === evt.newIndex) return;
          try {
            await api(`/tasks/${taskId}`, { method: "PUT", body: JSON.stringify({ status: newStatus }) });
            toast(`Moved to ${newStatus}`);
            board.querySelectorAll(".kanban-cards").forEach(c => {
              const badge = document.getElementById(`kc-${c.dataset.status.replace(/ /g, "-")}`);
              if (badge) badge.textContent = c.querySelectorAll(".kanban-card").length;
            });
          } catch (e) {
            toast(e.message, "error");
            await loadTasks();
          }
        }
      });
    });
  }
}

// ===== View toggle =====
function setView(mode) {
  viewMode = mode;
  localStorage.setItem("taskpilot_view", mode);
  document.querySelectorAll(".view-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.view === mode));
  const grid = document.getElementById("taskGrid");
  const kanban = document.getElementById("kanbanBoard");
  if (grid) grid.style.display = mode === "kanban" ? "none" : "";
  if (kanban) kanban.style.display = mode === "kanban" ? "" : "none";
}

// ===== Load & render tasks =====
async function loadTasks() {
  await loadLookups();
  const params = new URLSearchParams();
  const pageQuery = new URLSearchParams(location.search).get("q");
  const search = document.getElementById("taskSearch")?.value || pageQuery;
  const status = document.getElementById("statusFilter")?.value;
  const priority = document.getElementById("priorityFilter")?.value;
  const projectId = document.getElementById("projectId")?.value || document.getElementById("projectFilter")?.value;
  if (search) params.set("search", search);
  if (status) params.set("status", status);
  if (priority) params.set("priority", priority);
  if (projectId) params.set("project_id", projectId);
  tasks = await api(`/tasks?${params.toString()}`);

  const grid = document.getElementById("taskGrid");
  const kanban = document.getElementById("kanbanBoard");
  const projectGrid = document.getElementById("projectTaskGrid");

  if (projectGrid) {
    projectGrid.innerHTML = tasks.length ? tasks.map(taskCard).join("") : `<div class="empty-state">No tasks yet.</div>`;
    return;
  }
  if (grid && kanban) {
    if (viewMode === "kanban") {
      grid.style.display = "none";
      kanban.style.display = "";
      renderKanban(tasks);
    } else {
      kanban.style.display = "none";
      grid.style.display = "";
      grid.innerHTML = tasks.length ? tasks.map(taskCard).join("") : `<div class="empty-state">No tasks match this view.</div>`;
    }
  } else if (grid) {
    grid.innerHTML = tasks.length ? tasks.map(taskCard).join("") : `<div class="empty-state">No tasks match this view.</div>`;
  }
}

// ===== Project card with progress bar + member avatars =====
function projectCard(project) {
  const pct = project.task_count ? Math.round((project.completed_task_count || 0) / project.task_count * 100) : 0;
  const members = project.members || [];
  const avatars = members.slice(0, 4).map(m =>
    `<span class="avatar avatar-sm" title="${escapeHtml(m.name)}">${escapeHtml(m.name[0].toUpperCase())}</span>`
  ).join("");
  const overflow = members.length > 4
    ? `<span class="avatar avatar-sm" style="font-size:10px;color:var(--muted);">+${members.length - 4}</span>` : "";
  const admin = store.user?.role === "Admin";
  return `
    <article class="project-card">
      <h3>${escapeHtml(project.title)}</h3>
      <p class="muted">${escapeHtml(project.description || "No description")}</p>
      <div class="project-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
        <div class="card-meta" style="margin-top:4px;">
          <span class="muted" style="font-size:12px;">${pct}% complete</span>
          <span class="muted" style="font-size:12px;">${project.task_count} task${project.task_count !== 1 ? "s" : ""}</span>
        </div>
      </div>
      <div class="card-meta">
        <div class="avatar-stack">${avatars}${overflow}</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          <a class="ghost-btn" href="/projects-view/${project.id}">Open</a>
          ${admin ? `<button class="ghost-btn" data-edit-project="${project.id}">Edit</button><button class="danger-btn" data-delete-project="${project.id}">Delete</button>` : ""}
        </div>
      </div>
    </article>`;
}

async function loadProjectsPage() {
  await loadLookups();
  const query = (document.getElementById("projectSearch")?.value || "").toLowerCase();
  const grid = document.getElementById("projectsGrid");
  if (!grid) return;
  const visible = projects.filter(p => p.title.toLowerCase().includes(query));
  grid.innerHTML = visible.length ? visible.map(projectCard).join("") : `<div class="empty-state">No projects yet.</div>`;
}

async function loadProjectDetails() {
  const id = document.getElementById("projectId")?.value;
  if (!id) return;
  await loadLookups();
  const project = await api(`/projects/${id}`);
  document.getElementById("projectTitle").textContent = project.title;
  document.getElementById("projectDescription").textContent = project.description || "No description";
  document.getElementById("projectMembers").innerHTML = project.members.map(m => `
    <span class="avatar" title="${escapeHtml(m.name)}">${escapeHtml(m.name[0] || "?")}</span>
    ${store.user?.role === "Admin" ? `<button class="icon-btn" title="Remove ${escapeHtml(m.name)}" data-remove-member="${m.id}">✕</button>` : ""}
  `).join("");
  const memberSelect = document.getElementById("memberSelect");
  if (memberSelect) {
    const existing = new Set(project.members.map(m => m.id));
    memberSelect.innerHTML = users.filter(u => !existing.has(u.id))
      .map(u => `<option value="${u.id}">${escapeHtml(u.name)}</option>`).join("");
  }
  await loadTasks();
}

// ===== Task modal =====
function openTaskModal(task = {}) {
  const modal = document.getElementById("taskModal");
  const form = document.getElementById("taskForm");
  if (!modal || !form) return;
  fillTaskSelects(form);
  form.id.value = task.id || "";
  form.title.value = task.title || "";
  form.description.value = task.description || "";
  form.project_id.value = task.project_id || document.getElementById("projectId")?.value || projects[0]?.id || "";
  form.assigned_to.value = task.assigned_to || "";
  form.status.value = task.status || "Pending";
  form.priority.value = task.priority || "Medium";
  form.task_type.value = task.task_type || "Feature";
  form.due_date.value = task.due_date || "";
  modal.showModal();
}

// ===== Wire all events =====
function wireEvents() {
  document.getElementById("newTaskBtn")?.addEventListener("click", () => openTaskModal());

  document.getElementById("taskForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    payload.project_id = Number(payload.project_id);
    payload.assigned_to = payload.assigned_to ? Number(payload.assigned_to) : null;
    const id = payload.id; delete payload.id;
    try {
      await api(id ? `/tasks/${id}` : "/tasks", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
      document.getElementById("taskModal").close();
      toast(id ? "Task updated" : "Task created");
      await loadTasks();
    } catch (e) { toast(e.message, "error"); }
  });

  document.getElementById("taskSearch")?.addEventListener("input", () => loadTasks().catch(e => toast(e.message, "error")));
  document.getElementById("statusFilter")?.addEventListener("change", () => loadTasks().catch(e => toast(e.message, "error")));
  document.getElementById("priorityFilter")?.addEventListener("change", () => loadTasks().catch(e => toast(e.message, "error")));
  document.getElementById("projectFilter")?.addEventListener("change", () => loadTasks().catch(e => toast(e.message, "error")));
  document.getElementById("projectSearch")?.addEventListener("input", loadProjectsPage);

  document.querySelectorAll(".view-btn").forEach(btn => btn.addEventListener("click", () => setView(btn.dataset.view)));

  document.getElementById("newProjectBtn")?.addEventListener("click", () => {
    const form = document.getElementById("projectForm");
    form.reset(); form.id.value = "";
    document.getElementById("projectModal").showModal();
  });

  document.getElementById("projectForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    const id = payload.id; delete payload.id;
    try {
      await api(id ? `/projects/${id}` : "/projects", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
      document.getElementById("projectModal").close();
      toast(id ? "Project updated" : "Project created");
      await loadProjectsPage();
    } catch (e) { toast(e.message, "error"); }
  });

  document.getElementById("addMemberBtn")?.addEventListener("click", async () => {
    const projectId = document.getElementById("projectId")?.value;
    const userId = document.getElementById("memberSelect")?.value;
    if (!projectId || !userId) return;
    try {
      await api(`/projects/${projectId}/members`, { method: "POST", body: JSON.stringify({ user_id: Number(userId) }) });
      toast("Member added");
      await loadProjectDetails();
    } catch (e) { toast(e.message, "error"); }
  });

  document.addEventListener("click", async (event) => {
    const taskEdit   = event.target.closest("[data-edit-task]")?.dataset.editTask;
    const taskDelete = event.target.closest("[data-delete-task]")?.dataset.deleteTask;
    const projEdit   = event.target.closest("[data-edit-project]")?.dataset.editProject;
    const projDelete = event.target.closest("[data-delete-project]")?.dataset.deleteProject;
    const rmMember   = event.target.closest("[data-remove-member]")?.dataset.removeMember;

    if (taskEdit) openTaskModal(tasks.find(t => t.id === Number(taskEdit)));

    if (taskDelete && confirm("Delete this task?")) {
      await api(`/tasks/${taskDelete}`, { method: "DELETE" });
      toast("Task deleted");
      await loadTasks();
    }
    if (projEdit) {
      const p = projects.find(p => p.id === Number(projEdit));
      const form = document.getElementById("projectForm");
      form.id.value = p.id; form.title.value = p.title; form.description.value = p.description || "";
      document.getElementById("projectModal").showModal();
    }
    if (projDelete && confirm("Delete this project and all its tasks?")) {
      await api(`/projects/${projDelete}`, { method: "DELETE" });
      toast("Project deleted");
      await loadProjectsPage();
    }
    if (rmMember && confirm("Remove this member?")) {
      await api(`/projects/${document.getElementById("projectId").value}/members/${rmMember}`, { method: "DELETE" });
      toast("Member removed");
      await loadProjectDetails();
    }
  });

  document.addEventListener("change", async (event) => {
    const statusId = event.target.dataset.status;
    if (statusId) {
      try {
        await api(`/tasks/${statusId}`, { method: "PUT", body: JSON.stringify({ status: event.target.value }) });
        toast(`Moved to ${event.target.value}`);
        await loadTasks();
      } catch (e) { toast(e.message, "error"); }
    }
    const roleId = event.target.dataset.userRole;
    if (roleId) {
      try {
        await api(`/users/${roleId}`, { method: "PUT", body: JSON.stringify({ role: event.target.value }) });
        toast(`Role updated to ${event.target.value}`);
      } catch (e) { toast(e.message, "error"); }
    }
  });
}

// ===== Users page =====
async function loadUsersPage() {
  const table = document.getElementById("usersTable");
  if (!table) return;
  try {
    const rows = await api("/users");
    table.innerHTML = rows.map(u => `
      <tr>
        <td>${escapeHtml(u.name)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td><span class="pill">${u.role}</span></td>
        <td>${new Date(u.created_at).toLocaleDateString()}</td>
        <td>
          <select data-user-role="${u.id}">
            <option ${u.role === "Admin" ? "selected" : ""}>Admin</option>
            <option ${u.role === "Member" ? "selected" : ""}>Member</option>
          </select>
        </td>
      </tr>`).join("");
  } catch (e) { toast(e.message, "error"); }
}

// ===== Profile page =====
async function loadProfile() {
  const form = document.getElementById("profileForm");
  if (!form) return;
  const user = await api("/me");
  document.getElementById("profileName").value = user.name;
  document.getElementById("profileEmail").value = user.email;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form));
    if (payload.password && scorePasswordLocal(payload.password) < 5) {
      toast("Please use a stronger password.", "error"); return;
    }
    try {
      const updated = await api("/profile", { method: "PUT", body: JSON.stringify(payload) });
      store.setSession(store.token, updated);
      toast("Profile updated");
    } catch (e) { toast(e.message, "error"); }
  });
}

// ===== Init =====
document.addEventListener("DOMContentLoaded", async () => {
  wireEvents();
  document.querySelectorAll(".view-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.view === viewMode));
  try {
    if (document.getElementById("taskGrid")) await loadTasks();
    if (document.getElementById("projectsGrid")) await loadProjectsPage();
    if (document.getElementById("projectId")) await loadProjectDetails();
    await loadUsersPage();
    await loadProfile();
  } catch (e) { toast(e.message, "error"); }
});
