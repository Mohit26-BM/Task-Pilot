const store = {
  get token() { return localStorage.getItem("taskpilot_token"); },
  get user() { try { return JSON.parse(localStorage.getItem("taskpilot_user")); } catch { return null; } },
  setSession(token, user) {
    localStorage.setItem("taskpilot_token", token);
    localStorage.setItem("taskpilot_user", JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem("taskpilot_token");
    localStorage.removeItem("taskpilot_user");
  }
};

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (store.token) headers.Authorization = `Bearer ${store.token}`;
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401 && path !== "/login" && path !== "/signup") {
    store.clear();
    flash("Your session has expired. Please sign in again.", "error");
    location.href = "/login";
    throw new Error("Session expired");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

function toast(message, type = "success") {
  const host = document.getElementById("toastHost");
  if (!host) return;
  const node = document.createElement("div");
  node.className = `toast ${type}`;
  node.textContent = message;
  host.appendChild(node);
  setTimeout(() => node.remove(), 3200);
}

function flash(message, type = "success") {
  sessionStorage.setItem("taskpilot_flash", JSON.stringify({ message, type }));
}

function consumeFlash() {
  try {
    const raw = sessionStorage.getItem("taskpilot_flash");
    if (!raw) return;
    sessionStorage.removeItem("taskpilot_flash");
    const { message, type } = JSON.parse(raw);
    if (message) toast(message, type || "success");
  } catch {
    sessionStorage.removeItem("taskpilot_flash");
  }
}

function formatDate(value) {
  if (!value) return "No due date";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

function requireAuth() {
  const publicPaths = ["/", "/login", "/signup"];
  if (!store.token && !publicPaths.includes(location.pathname)) {
    location.href = "/login";
    return;
  }
  const adminPaths = ["/users-view"];
  if (store.user && store.user.role !== "Admin" && adminPaths.includes(location.pathname)) {
    location.href = "/dashboard";
  }
}

function initShell() {
  const user = store.user;
  const sidebarUser = document.getElementById("sidebarUser");
  const sidebarRole = document.getElementById("sidebarRole");
  if (user && sidebarUser) {
    sidebarUser.textContent = user.name;
    sidebarRole.textContent = user.role;
  }
  document.querySelectorAll("[data-admin-only], .admin-only").forEach((el) => {
    if (!user || user.role !== "Admin") el.style.display = "none";
  });
  document.querySelectorAll("[data-nav]").forEach((link) => {
    const key = link.dataset.nav;
    if (location.pathname.includes(key) || (key === "dashboard" && location.pathname === "/dashboard")) link.classList.add("active");
  });
  document.getElementById("logoutBtn")?.addEventListener("click", () => {
    store.clear();
    flash("Logout successful");
    location.href = "/login";
  });
  document.getElementById("sidebarToggle")?.addEventListener("click", () => {
    document.getElementById("sidebar")?.classList.toggle("open");
  });
  document.getElementById("globalSearch")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.currentTarget.value.trim()) {
      location.href = `/tasks-view?q=${encodeURIComponent(event.currentTarget.value.trim())}`;
    }
  });
}

requireAuth();
document.addEventListener("DOMContentLoaded", () => {
  initShell();
  consumeFlash();
});
