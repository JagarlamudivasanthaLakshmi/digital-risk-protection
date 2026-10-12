document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-monitoring-filter]").forEach((filter) => {
    filter.addEventListener("input", () => {
      const query = filter.value.toLowerCase();
      document.querySelectorAll("[data-monitoring-row]").forEach((row) => {
        row.hidden = !row.textContent.toLowerCase().includes(query);
      });
    });

    document.querySelectorAll("[data-analyze-item]").forEach((button) => {
      button.addEventListener("click", async () => {
        const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1];
        if (!csrfToken) {
          window.alert("Security token is missing. Reload the page and try again.");
          return;
        }
        button.disabled = true;
        button.textContent = "Scanning…";
        try {
          const response = await fetch(button.dataset.analyzeUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken,
              Accept: "application/json",
            },
            body: JSON.stringify({ item_id: button.dataset.analyzeItem }),
          });
          const result = await response.json();
          if (!response.ok) {
            throw new Error(result.detail || "Unable to scan this item.");
          }
          window.location.reload();
        } catch (error) {
          window.alert(error.message || "The scan failed. Please try again.");
          button.disabled = false;
          button.textContent = "Scan / AI explain";
        }
      });
    });
  });
});
