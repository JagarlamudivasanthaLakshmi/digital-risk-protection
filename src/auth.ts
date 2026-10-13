import {
  AuthError,
  getSettings,
  getUser,
  handleAuthCallback,
  login,
  MissingIdentityError,
  signup,
} from "@netlify/identity";

const notice = document.querySelector<HTMLElement>("#notice");
const loginForm = document.querySelector<HTMLFormElement>("#login-form");
const signupForm = document.querySelector<HTMLFormElement>("#signup-form");
const signupDetails = signupForm?.closest("details");
const fallback = document.querySelector<HTMLElement>("#local-auth-fallback");
let identityReady = false;
let signupEnabled = true;

const showMessage = (message: string, isError = false) => {
  if (!notice) return;
  notice.textContent = message;
  notice.style.color = isError ? "#9e2f29" : "#28613c";
};

function setAuthControlsDisabled(disabled: boolean): void {
  for (const button of document.querySelectorAll<HTMLButtonElement>(
    "#login-form button, #signup-form button",
  )) {
    button.disabled = disabled;
  }
}

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

loginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!identityReady) {
    showMessage("Authentication is not ready. Enable Netlify Identity for this site and reload.", true);
    return;
  }
  const form = event.currentTarget as HTMLFormElement;
  try {
    await login(formValue(form, "email"), formValue(form, "password"));
    window.location.assign("/dashboard.html");
  } catch (error) {
    if (showIdentityUnavailable(error)) {
      identityReady = false;
      setAuthControlsDisabled(true);
      return;
    }
    showMessage(error instanceof Error ? error.message : "Sign in failed.", true);
  }
});

signupForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!identityReady) {
    showMessage("Account creation is not ready. Enable Netlify Identity for this site and reload.", true);
    return;
  }
  if (!signupEnabled) {
    showMessage("Account creation is disabled. Enable sign-ups in this site's Netlify Identity settings.", true);
    return;
  }
  const form = event.currentTarget as HTMLFormElement;
  try {
    await signup(formValue(form, "email"), formValue(form, "password"));
    if (await getUser()) window.location.assign("/dashboard.html");
    else showMessage("Account created. Check your email to confirm it, then sign in.");
  } catch (error) {
    if (showIdentityUnavailable(error)) {
      identityReady = false;
      setAuthControlsDisabled(true);
      return;
    }
    showMessage(error instanceof Error ? error.message : "Account creation failed.", true);
  }
});

async function initializeAuthPage() {
  if (isLocalHost()) {
    showLocalDjangoFallback();
    return;
  }

  setAuthControlsDisabled(true);
  showMessage("Connecting to account services…");
  try {
    const settings = await getSettings();
    signupEnabled = !settings.disableSignup && settings.providers.email;
    await handleAuthCallback();
    if (await getUser()) {
      window.location.replace("/dashboard.html");
      return;
    }
    identityReady = true;
    setAuthControlsDisabled(false);
    if (!signupEnabled) {
      if (signupDetails) signupDetails.hidden = true;
      showMessage("Account creation is disabled. Enable email sign-ups in this site's Netlify Identity settings.", true);
    } else {
      showMessage("");
    }
  } catch (error) {
    if (showIdentityUnavailable(error)) {
      setAuthControlsDisabled(true);
      return;
    }
    setAuthControlsDisabled(true);
    const detail = error instanceof Error ? error.message : "Unknown Identity error.";
    showMessage(
      `Could not connect to Netlify Identity (${detail}). Enable Identity and email/password sign-ups for this site, then reload.`,
      true,
    );
  }
}

void initializeAuthPage();
