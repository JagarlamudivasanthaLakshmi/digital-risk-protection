import { AuthError, getUser, handleAuthCallback, login, MissingIdentityError, signup } from "@netlify/identity";

const notice = document.querySelector<HTMLElement>("#notice");
const loginForm = document.querySelector<HTMLFormElement>("#login-form");
const signupForm = document.querySelector<HTMLFormElement>("#signup-form");
const signupDetails = signupForm?.closest("details");
const fallback = document.querySelector<HTMLElement>("#local-auth-fallback");
const showMessage = (message: string, isError = false) => {
  if (!notice) return;
  notice.textContent = message;
  notice.style.color = isError ? "#9e2f29" : "#28613c";
};

function formValue(form: HTMLFormElement, name: string): string {
  return new FormData(form).get(name)?.toString().trim() ?? "";
}

function isLocalHost(): boolean {
  return window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
}

function showLocalDjangoFallback(): void {
  loginForm?.setAttribute("hidden", "");
  signupDetails?.setAttribute("hidden", "");
  const djangoBase = `${window.location.protocol}//${window.location.hostname}:8002`;
  const loginLink = document.querySelector<HTMLAnchorElement>("#django-login-link");
  const registerLink = document.querySelector<HTMLAnchorElement>("#django-register-link");
  if (loginLink) loginLink.href = new URL("/accounts/login/", djangoBase).href;
  if (registerLink) registerLink.href = new URL("/accounts/register/", djangoBase).href;
  if (fallback) fallback.hidden = false;
  showMessage("Using Django accounts on port 8002 for local sign-in.");
}

function showIdentityUnavailable(error: unknown): boolean {
  const identityNotFound = error instanceof MissingIdentityError
    || (error instanceof AuthError && error.status === 404)
    || (error instanceof Error && error.message.trim().toLowerCase() === "not found");
  if (!identityNotFound) {
    return false;
  }

  if (isLocalHost()) {
    showLocalDjangoFallback();
  } else {
    loginForm?.setAttribute("hidden", "");
    signupDetails?.setAttribute("hidden", "");
    showMessage("Netlify Identity is unavailable. Enable Identity for this Netlify site, then try again.", true);
  }
  return true;
}

async function initializeAuthPage() {
  if (isLocalHost()) {
    showLocalDjangoFallback();
    return;
  }

  try {
    await handleAuthCallback();
    if (await getUser()) window.location.replace("/dashboard.html");
  } catch (error) {
    if (showIdentityUnavailable(error)) return;
    showMessage(error instanceof Error ? error.message : "Netlify Identity could not be reached.", true);
    return;
  }

  loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    try {
      await login(formValue(form, "email"), formValue(form, "password"));
      window.location.assign("/dashboard.html");
    } catch (error) {
      if (showIdentityUnavailable(error)) return;
      showMessage(error instanceof Error ? error.message : "Sign in failed.", true);
    }
  });

  signupForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    try {
      await signup(formValue(form, "email"), formValue(form, "password"));
      if (await getUser()) window.location.assign("/dashboard.html");
      else showMessage("Account created. Check your email to confirm it, then sign in.");
    } catch (error) {
      if (showIdentityUnavailable(error)) return;
      showMessage(error instanceof Error ? error.message : "Account creation failed.", true);
    }
  });
}

void initializeAuthPage();
