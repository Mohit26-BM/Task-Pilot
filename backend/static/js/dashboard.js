Chart.defaults.color = "#94a3b8";
Chart.defaults.font.family = "Inter, system-ui, sans-serif";
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.usePointStyle = true;

function entries(obj) {
  const pairs = Object.entries(obj || {});
  return pairs.length ? pairs : [["No data", 1]];
}

function statusClass(status) {
  return { "Pending": "status-pending", "In Progress": "status-progress", "Review": "status-review", "Completed": "status-completed" }[status] || "status-pending";
}

function createChart(id, type, pairs, colors) {
  const ctx = document.getElementById(id);
  if (!ctx) return;
  const labels = pairs.map((x) => x[0]);
  const values = pairs.map((x) => x[1]);
  const isLine = type === "line";
  const isBar = type === "bar";

  new Chart(ctx, {
    type,
    data: {
      labels,
      datasets: [{
        data: values,
        label: isBar || isLine ? "Tasks" : undefined,
        backgroundColor: isBar || isLine ? colors[0] : colors,
        borderColor: isLine ? colors[0] : isBar ? "#8b5cf6" : "rgba(255,255,255,.12)",
        borderWidth: isLine ? 3 : 1,
        tension: .35,
        fill: isLine,
        pointBackgroundColor: colors[0],
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 850, easing: "easeOutQuart" },
      plugins: {
        legend: { display: !isBar && !isLine, position: "bottom" },
        tooltip: {
          backgroundColor: "#111827",
          borderColor: "rgba(255,255,255,.08)",
          borderWidth: 1,
        },
      },
      scales: isBar || isLine ? {
        x: { grid: { color: "rgba(255,255,255,.04)" } },
        y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "rgba(255,255,255,.08)" } },
      } : {},
    },
  });
}

async function loadDashboard() {
  try {
    const data = await api("/dashboard/stats");
    const cardLabels = [
      ["Total Tasks", data.cards.total_tasks],
      ["Completed", data.cards.completed_tasks],
      ["Pending", data.cards.pending_tasks],
      ["Overdue", data.cards.overdue_tasks],
      ["Active Projects", data.cards.active_projects],
    ];
    document.getElementById("statsGrid").innerHTML = cardLabels.map(([label, value], index) => `
      <article class="stat-card" style="animation-delay:${index * 55}ms"><span>${label}</span><strong>${value}</strong></article>
    `).join("");

    createChart("statusChart", "pie", entries(data.status_distribution), ["#f59e0b", "#8b5cf6", "#3b82f6", "#10b981"]);
    createChart("priorityChart", "doughnut", entries(data.priority_distribution), ["#10b981", "#f59e0b", "#fb7185", "#ef4444"]);
    createChart("projectChart", "bar", entries(data.tasks_per_project), ["#6366f1"]);

    const timeline = Object.entries(data.completed_over_time || {});
    createChart("timelineChart", "line", timeline.length ? timeline : [["No data", 0]], ["#10b981"]);

    document.getElementById("recentTasks").innerHTML = data.recent_tasks.length ? data.recent_tasks.map((task) => `
      <div class="activity-item"><div><strong>${task.title}</strong><div class="muted">${task.project_title || "No project"} - ${task.assignee_name}</div></div><span class="pill ${statusClass(task.status)}">${task.status}</span></div>
    `).join("") : `<div class="empty-state">No recent tasks yet.</div>`;
  } catch (error) {
    toast(error.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", loadDashboard);
