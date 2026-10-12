document.addEventListener("DOMContentLoaded", () => {
  const domainField = document.querySelector("#id_official_domains");
  if (domainField) domainField.setAttribute("placeholder", '["example.com"]');
});
