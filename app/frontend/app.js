const tokenKey = "orvencore_access_token";
const refreshKey = "orvencore_refresh_token";

const loginTab = document.querySelector("#login-tab");
const registerTab = document.querySelector("#register-tab");
const loginForm = document.querySelector("#login-form");
const registerForm = document.querySelector("#register-form");
const discordForm = document.querySelector("#discord-form");
const notice = document.querySelector("#notice");
const accountPanel = document.querySelector("#account-panel");
const logoutButton = document.querySelector("#logout-button");
const apiDot = document.querySelector("#api-dot");
const apiStatus = document.querySelector("#api-status");
const discordLinkNote = document.querySelector("#discord-link-note");

const linkParams = new URLSearchParams(window.location.search);
const pendingDiscord = {
  link_token: linkParams.get("discord_link_token") || "",
  discord_user_id: linkParams.get("discord_id") || "",
  username: linkParams.get("discord_username") || "",
  avatar_url: linkParams.get("discord_avatar") || "",
};

function setNotice(message, type = "") {
  notice.textContent = message;
  notice.className = type ? `notice ${type}` : "notice";
}

function setMode(mode) {
  const isLogin = mode === "login";
  loginTab.classList.toggle("active", isLogin);
  registerTab.classList.toggle("active", !isLogin);
  loginForm.classList.toggle("hidden", !isLogin);
  registerForm.classList.toggle("hidden", isLogin);
  setNotice("");
}

function formJson(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  const token = localStorage.getItem(tokenKey);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item) => item.msg).join(", ")
      : body?.detail;
    throw new Error(detail || "Request failed");
  }

  return body;
}

async function login(payload) {
  const tokens = await api("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  localStorage.setItem(tokenKey, tokens.access_token);
  localStorage.setItem(refreshKey, tokens.refresh_token);
  await loadAccount();
}

function renderPills(containerId, values) {
  const container = document.querySelector(containerId);
  container.innerHTML = "";
  for (const value of values) {
    const item = document.createElement("span");
    item.className = "pill";
    item.textContent = value;
    container.append(item);
  }
}

async function loadAccount() {
  const [account, permissionSummary, sessions] = await Promise.all([
    api("/auth/me"),
    api("/permissions/me"),
    api("/auth/sessions"),
  ]);

  document.querySelector("#account-title").textContent = account.display_name || account.username;
  document.querySelector("#account-email").textContent = account.email;
  document.querySelector("#discord-state").textContent = account.discord_account
    ? `${account.discord_account.username} (${account.discord_account.discord_user_id})`
    : "Not linked";

  renderPills("#roles", permissionSummary.roles);
  renderPills("#permissions", permissionSummary.permissions);
  renderSessions(sessions);
  document.querySelector("#admin-placeholder").classList.toggle(
    "hidden",
    !permissionSummary.permissions.some((permission) => permission.startsWith("admin.")),
  );

  if (account.discord_account) {
    discordForm.elements.discord_user_id.value = account.discord_account.discord_user_id;
    discordForm.elements.username.value = account.discord_account.username;
    discordForm.elements.avatar_url.value = account.discord_account.avatar_url || "";
    discordLinkNote.textContent = "";
  } else if (pendingDiscord.link_token) {
    const discordPayload = await api(`/auth/discord/callback?token=${encodeURIComponent(pendingDiscord.link_token)}`);
    pendingDiscord.discord_user_id = discordPayload.discord_user_id;
    pendingDiscord.username = discordPayload.username;
    pendingDiscord.avatar_url = discordPayload.avatar_url || "";
    discordForm.elements.discord_user_id.value = pendingDiscord.discord_user_id;
    discordForm.elements.username.value = pendingDiscord.username;
    discordForm.elements.avatar_url.value = pendingDiscord.avatar_url;
    discordLinkNote.textContent = "Verified Discord link detected from the bot. Link it to this OrvenCore account.";
  } else if (pendingDiscord.discord_user_id) {
    discordForm.elements.discord_user_id.value = pendingDiscord.discord_user_id;
    discordForm.elements.username.value = pendingDiscord.username;
    discordForm.elements.avatar_url.value = pendingDiscord.avatar_url;
    discordLinkNote.textContent = "Discord identity detected from the bot. Link it to this OrvenCore account.";
  }

  accountPanel.classList.remove("hidden");

  if (!account.discord_account && (pendingDiscord.link_token || pendingDiscord.discord_user_id)) {
    await linkPendingDiscord();
  }
}

function renderSessions(sessions) {
  const container = document.querySelector("#sessions");
  container.innerHTML = "";
  for (const session of sessions) {
    const item = document.createElement("div");
    item.className = "session-item";
    const created = new Date(session.created_at).toLocaleString();
    item.innerHTML = `<span>${session.user_agent || "Unknown device"}</span><span>${created}</span>`;
    container.append(item);
  }
}

async function restoreSession() {
  if (localStorage.getItem(tokenKey)) {
    try {
      await loadAccount();
      return;
    } catch {
      localStorage.removeItem(tokenKey);
    }
  }

  const refreshToken = localStorage.getItem(refreshKey);
  if (!refreshToken) {
    return;
  }

  try {
    const tokens = await api("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    localStorage.setItem(tokenKey, tokens.access_token);
    localStorage.setItem(refreshKey, tokens.refresh_token);
    await loadAccount();
  } catch {
    localStorage.removeItem(tokenKey);
    localStorage.removeItem(refreshKey);
  }
}

async function linkPendingDiscord() {
  if (!pendingDiscord.link_token && (!pendingDiscord.discord_user_id || !pendingDiscord.username)) {
    return;
  }

  await api("/discord/me", {
    method: "PUT",
    body: JSON.stringify(
      pendingDiscord.link_token
        ? { link_token: pendingDiscord.link_token }
        : pendingDiscord,
    ),
  });

  pendingDiscord.link_token = "";
  pendingDiscord.discord_user_id = "";
  await loadAccount();
  setNotice("Discord account linked. You can return to Discord now.", "success");
}

async function checkHealth() {
  try {
    await api("/health");
    apiDot.className = "status-dot online";
    apiStatus.textContent = "API online";
  } catch {
    apiDot.className = "status-dot offline";
    apiStatus.textContent = "API offline";
  }
}

loginTab.addEventListener("click", () => setMode("login"));
registerTab.addEventListener("click", () => setMode("register"));

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setNotice("Signing in...");
  try {
    await login(formJson(loginForm));
    setNotice("Logged in.", "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = formJson(registerForm);
  setNotice("Creating account...");
  try {
    await api("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await login({
      username_or_email: payload.username,
      password: payload.password,
    });
    setNotice("Account created and logged in.", "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
});

discordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setNotice("Linking Discord...");
  try {
    await api("/discord/me", {
      method: "PUT",
      body: JSON.stringify(formJson(discordForm)),
    });
    await loadAccount();
    setNotice("Discord account linked.", "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
});

logoutButton.addEventListener("click", () => {
  const refreshToken = localStorage.getItem(refreshKey);
  if (refreshToken) {
    api("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {});
  }
  localStorage.removeItem(tokenKey);
  localStorage.removeItem(refreshKey);
  accountPanel.classList.add("hidden");
  setNotice("Logged out.");
});

checkHealth();
restoreSession();
