import { getUser, handleAuthCallback, login, signup } from "@netlify/identity";

const notice = document.querySelector<HTMLElement>("#notice");
const showMessage = (message: string, isError = false) => {
  if (!notice) return;
  notice.textContent = message;
  notice.style.color = isError ? "#9e2f29" : "#28613c";
};

function formValue(form: HTMLFormElement, name: string): string {
  return new FormData(form).get(name)?.toString().trim() ?? "";
}

async function initializeAuthPage() {
  try {
    await handleAuthCallback();
    if (await getUser()) window.location.replace("/dashboard.html");
  } catch (error) {
    showMessage(error instanceof Error ? error.message : "Netlify Identity could not be reached.", true);
  }

  document.querySelector<HTMLFormElement>("#login-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    try {
      await login(formValue(form, "email"), formValue(form, "password"));
      window.location.assign("/dashboard.html");
    } catch (error) {
      showMessage(error instanceof Error ? error.message : "Sign in failed.", true);
    }
  });

  document.querySelector<HTMLFormElement>("#signup-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    try {
      const user = await signup(formValue(form, "email"), formValue(form, "password"));
      if (user) window.location.assign("/dashboard.html");
      else showMessage("Account created. Check your email to confirm the account.");
    } catch (error) {
      showMessage(error instanceof Error ? error.message : "Account creation failed.", true);
    }
  });
}

void initializeAuthPage();
