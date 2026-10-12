import { getUser, logout } from "@netlify/identity";

type Brand = {
  id: number;
  name: string;
  description: string;
  officialDomains: string[];
  officialPublishers: string[];
  officialSocialAccounts: string[];
  officialApps: string[];
};
type Finding = {
  id: number;
  riskScore: number;
  severity: string;
  signals: Array<{ signal?: string }>;
  explanation: string;
  item: { name: string; url: string; source: string } | null;
  alert: { id: number; status: string; notes: string } | null;
};
type AlertRecord = { id: number; status: string; notes: string; finding: { riskScore: number; severity: string } };
type DashboardResponse = {
  brands: Brand[];
  findings: Finding[];
  alerts: AlertRecord[];
  stats: Record<string, number>;
};

const notice = document.querySelector<HTMLElement>("#notice");
const text = (tag: string, value: string, className?: string): HTMLElement => {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
};
const announce = (message: string, isError = false) => {
  if (!notice) return;
  notice.textContent = message;
  notice.style.color = isError ? "#9e2f29" : "#28613c";
};
const lines = (value: FormDataEntryValue | null): string[] =>
  String(value ?? "").split(/\r?\n/).map((entry) => entry.trim()).filter(Boolean);

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers: { "content-type": "application/json", ...options?.headers },
  });
  const payload: unknown = await response.json();
  if (!response.ok) {
    const error = payload && typeof payload === "object" && "error" in payload
      ? String(payload.error)
      : `Request failed with HTTP ${response.status}.`;
    throw new Error(error);
  }
  return payload as T;
}

function renderMetrics(stats: Record<string, number>) {
  const parent = document.querySelector("#metrics");
  if (!parent) return;
  parent.replaceChildren();
  const metrics = [
    ["Total detections", stats.detection_count ?? 0],
    ["Social findings", stats.social_detection_count ?? 0],
    ["App listings", stats.app_detection_count ?? 0],
    ["Monitored brands", stats.brand_count ?? 0],
  ];
  for (const [label, value] of metrics) {
    const card = text("article", "", "metric panel");
    card.append(text("span", String(label)), text("strong", String(value)));
    parent.append(card);
  }
}

function renderBrands(brands: Brand[]) {
  const list = document.querySelector("#brand-list");
  if (!list) return;
  list.replaceChildren();
  if (!brands.length) {
    list.append(text("p", "Add a brand profile to start monitoring.", "empty"));
    return;
  }
  for (const brand of brands) {
    const card = text("article", "", "brand-card");
    card.append(text("h3", brand.name));
    card.append(text("p", brand.description || "No description provided."));
    card.append(text("p", `Official domains: ${brand.officialDomains.join(", ") || "None configured"}`));
    const controls = text("div", "", "brand-controls");
    for (const [source, label] of [
      ["social", "Scan social"],
      ["app_store", "Scan Apple App Store"],
      ["google_play", "Scan Google Play"],
    ]) {
      const button = text("button", label) as HTMLButtonElement;
      button.type = "button";
      button.addEventListener("click", () => void runScan(brand, source, button));
      controls.append(button);
    }
    card.append(controls);
    list.append(card);
  }
}

function renderFindings(findings: Finding[]) {
  const list = document.querySelector("#finding-list");
  if (!list) return;
  list.replaceChildren();
  if (!findings.length) {
    list.append(text("p", "No detections yet. Run a source scan to check for candidate matches.", "empty"));
    return;
  }
  for (const finding of findings) {
    const card = text("article", "", "finding-card");
    card.append(text("h3", finding.item?.name ?? "Deleted monitored item"));
    card.append(text("p", finding.item?.url ?? finding.explanation));
    card.append(text("span", `${finding.severity.toUpperCase()} · ${finding.riskScore}/100`, "score"));
    const signals = text("div", "", "signal-list");
    for (const signal of finding.signals) {
      if (signal.signal) signals.append(text("span", signal.signal.replaceAll("_", " ")));
    }
    if (signals.childElementCount) card.append(signals);
    card.append(text("p", finding.explanation));
    list.append(card);
  }
}

async function refreshDashboard() {
  const data = await api<DashboardResponse>("/api/dashboard");
  renderMetrics(data.stats);
  renderBrands(data.brands);
  renderFindings(data.findings);
  renderAlerts(data.alerts);
}

function renderAlerts(alerts: AlertRecord[]) {
  const list = document.querySelector("#alert-list");
  if (!list) return;
  list.replaceChildren();
  if (!alerts.length) {
    list.append(text("p", "No alerts require investigation.", "empty"));
    return;
  }
  for (const alert of alerts) {
    const card = text("article", "", "alert-card");
    const details = text("div", "");
    details.append(text("strong", `Alert #${alert.id} · ${alert.finding.severity} risk`));
    details.append(text("p", alert.notes || "No investigation notes."));
    const select = document.createElement("select");
    select.setAttribute("aria-label", `Alert ${alert.id} status`);
    for (const status of ["open", "investigating", "resolved", "dismissed"]) {
      const option = document.createElement("option");
      option.value = status;
      option.textContent = status;
      option.selected = status === alert.status;
      select.append(option);
    }
    select.addEventListener("change", async () => {
      try {
        await api("/api/alerts", {
          method: "PATCH",
          body: JSON.stringify({ id: alert.id, status: select.value, notes: alert.notes }),
        });
        announce(`Alert #${alert.id} updated.`);
      } catch (error) {
        announce(error instanceof Error ? error.message : "Alert update failed.", true);
      }
    });
    card.append(details, select);
    list.append(card);
  }
}

async function runScan(brand: Brand, source: string, button: HTMLButtonElement) {
  button.disabled = true;
  announce(`Scanning ${brand.name} on ${source}…`);
  try {
    const result = await api<{ found: number; new: number; alerts: number }>("/api/scan", {
      method: "POST",
      body: JSON.stringify({ brandId: brand.id, source }),
    });
    announce(`Scan complete: ${result.found} candidates, ${result.new} new, ${result.alerts} new alerts.`);
    await refreshDashboard();
  } catch (error) {
    announce(error instanceof Error ? error.message : "Scan failed.", true);
  } finally {
    button.disabled = false;
  }
}

async function initializeDashboard() {
  try {
    const user = await getUser();
    if (!user) {
      window.location.replace("/");
      return;
    }
    const email = document.querySelector("#user-email");
    if (email) email.textContent = user.email ?? "";
    document.querySelector("#logout-button")?.addEventListener("click", async () => {
      try {
        await logout();
        window.location.assign("/");
      } catch (error) {
        announce(error instanceof Error ? error.message : "Sign out failed.", true);
      }
    });

    document.querySelector<HTMLFormElement>("#brand-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = event.currentTarget as HTMLFormElement;
      const data = new FormData(form);
      const body = {
        name: String(data.get("name") ?? "").trim(),
        description: String(data.get("description") ?? "").trim(),
        officialDomains: lines(data.get("officialDomains")),
        officialPublishers: lines(data.get("officialPublishers")),
        officialSocialAccounts: lines(data.get("officialSocialAccounts")),
        officialApps: lines(data.get("officialApps")),
      };
      try {
        await api("/api/brands", { method: "POST", body: JSON.stringify(body) });
        form.reset();
        announce("Brand profile created.");
        await refreshDashboard();
      } catch (error) {
        announce(error instanceof Error ? error.message : "Brand creation failed.", true);
      }
    });

    await refreshDashboard();
  } catch (error) {
    announce(error instanceof Error ? error.message : "Dashboard could not be loaded.", true);
  }
}

void initializeDashboard();
