document.addEventListener("DOMContentLoaded", async () => {
  const target = document.querySelector("[data-threat-graph]");
  if (!target) return;
  const response = await fetch("/correlation/api/", { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Threat graph request failed: ${response.status}`);
  target.textContent = JSON.stringify(await response.json());
});
