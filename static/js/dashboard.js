document.addEventListener("DOMContentLoaded", async () => {
  const target = document.querySelector("[data-dashboard-stats]");
  if (!target) return;
  const response = await fetch("/dashboard/api/stats/", { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Dashboard stats request failed: ${response.status}`);
  target.dataset.dashboardStats = JSON.stringify(await response.json());
});
