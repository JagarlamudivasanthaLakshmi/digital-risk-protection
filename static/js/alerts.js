document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-alert-status]").forEach((element) => {
    element.addEventListener("change", async () => {
      const response = await fetch(element.dataset.alertStatus, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRFToken": document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "" },
        body: JSON.stringify({ status: element.value }),
      });
      if (!response.ok) throw new Error(`Alert update failed: ${response.status}`);
    });
  });
});
