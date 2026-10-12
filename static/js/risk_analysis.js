document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-risk-score]").forEach((element) => {
    const score = Number(element.dataset.riskScore);
    element.setAttribute("aria-label", `Risk score ${score} out of 100`);
  });
});
