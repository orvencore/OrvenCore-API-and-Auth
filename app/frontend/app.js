const tokenKey = "orvencore_access_token";
const refreshKey = "orvencore_refresh_token";

const app = document.querySelector("#app");
const nav = document.querySelector("#nav");
const toast = document.querySelector("#toast");
const params = new URLSearchParams(window.location.search);

const pendingDiscord = {
  link_token: params.get("discord_link_token") || "",
  discord_user_id: params.get("discord_id") || "",
  username: params.get("discord_username") || "",
  avatar_url: params.get("discord_avatar") || "",
};

let state = {
  account: null,
  permissions: [],
  roles: [],
  services: [],
  serviceAccess: [],
  sessions: [],
};

function showToast(message, type = "") {
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  window.setTimeout(() => {
    toast.className = "toast";
  }, 3600);
}

function navigate(path) {
  window.history.pushState({}, "", path);
  render();
}

function preserveDiscord(path) {
  const query = new URLSearchParams();
  if (pendingDiscord.link_token) query.set("discord_link_token", pendingDiscord.link_token);
  if (pendingDiscord.discord_user_id) query.set("discord_id", pendingDiscord.discord_user_id);
  if (pendingDiscord.username) query.set("discord_username", pendingDiscord.username);
  if (pendingDiscord.avatar_url) query.set("discord_avatar", pendingDiscord.avatar_url);
  const qs = query.toString();
  return qs ? `${path}?${qs}` : path;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  const token = localStorage.getItem(tokenKey);
  if (token) headers.set("Authorization", `Bearer ${token}`);

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

async function restoreSession() {
  if (!localStorage.getItem(tokenKey) && localStorage.getItem(refreshKey)) {
    try {
      const tokens = await api("/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: localStorage.getItem(refreshKey) }),
      });
      localStorage.setItem(tokenKey, tokens.access_token);
      localStorage.setItem(refreshKey, tokens.refresh_token);
    } catch {
      localStorage.removeItem(tokenKey);
      localStorage.removeItem(refreshKey);
    }
  }
  await refreshState();
}

async function refreshState() {
  state.services = await api("/services");
  if (!localStorage.getItem(tokenKey)) {
    state.account = null;
    state.roles = [];
    state.permissions = [];
    state.serviceAccess = [];
    state.sessions = [];
    return;
  }
  try {
    const [account, permissions, serviceAccess, sessions] = await Promise.all([
      api("/auth/me"),
      api("/permissions/me"),
      api("/services/me"),
      api("/auth/sessions"),
    ]);
    state.account = account;
    state.roles = permissions.roles;
    state.permissions = permissions.permissions;
    state.serviceAccess = serviceAccess;
    state.sessions = sessions;
    await autoLinkDiscord();
  } catch {
    localStorage.removeItem(tokenKey);
    state.account = null;
  }
}

async function autoLinkDiscord() {
  if (!state.account || state.account.discord_account) return;
  if (!pendingDiscord.link_token && !pendingDiscord.discord_user_id) return;

  const body = pendingDiscord.link_token
    ? { link_token: pendingDiscord.link_token }
    : {
        discord_user_id: pendingDiscord.discord_user_id,
        username: pendingDiscord.username,
        avatar_url: pendingDiscord.avatar_url,
      };
  await api("/discord/me", { method: "PUT", body: JSON.stringify(body) });
  pendingDiscord.link_token = "";
  pendingDiscord.discord_user_id = "";
  pendingDiscord.username = "";
  pendingDiscord.avatar_url = "";
  state.account = await api("/auth/me");
  showToast("Discord account linked.");
}

function isAdmin() {
  return state.permissions.some((permission) => permission.startsWith("admin."));
}

function navLink(path, label) {
  const active = window.location.pathname === path ? "active" : "";
  return `<a href="${path}" data-link class="${active}">${label}</a>`;
}

function renderNav() {
  if (!state.account) {
    nav.innerHTML = [
      navLink("/apps", "Apps"),
      navLink("/login", "Login"),
      `<a href="/register" data-link class="primary">Register</a>`,
    ].join("");
    return;
  }

  nav.innerHTML = [
    navLink("/dashboard", "Dashboard"),
    navLink("/apps", "Apps"),
    navLink("/account", "Account"),
    isAdmin() ? navLink("/admin", "Admin") : "",
    `<button type="button" id="logout-nav">Logout</button>`,
  ].join("");
  document.querySelector("#logout-nav")?.addEventListener("click", logout);
}

function serviceCards(services, includeAccess = false) {
  return `<div class="grid">${services
    .map((service) => {
      const access = includeAccess
        ? service.has_access
          ? `<span class="status">Access granted</span>`
          : `<span class="status denied">Missing ${service.missing_permissions.join(", ") || "access"}</span>`
        : `<span class="status">${service.status}</span>`;
      const button = service.url
        ? `<a class="button" href="${service.url}">Open</a>`
        : `<span class="muted">Coming soon</span>`;
      return `<article class="card">
        ${access}
        <h3>${service.name}</h3>
        <p>${service.description}</p>
        <div class="pill-row">${service.required_permissions.map((p) => `<span class="pill">${p}</span>`).join("") || `<span class="pill">Public metadata</span>`}</div>
        ${button}
      </article>`;
    })
    .join("")}</div>`;
}

function homeView() {
  const cta = state.account
    ? `<a class="button primary" href="/dashboard" data-link>Open Dashboard</a>`
    : `<a class="button primary" href="${preserveDiscord("/register")}" data-link>Get Started</a>
       <a class="button" href="${preserveDiscord("/login")}" data-link>Log In</a>`;
  return `<section class="hero">
    <div>
      <p class="eyebrow">orvencore.com</p>
      <h1>One account. Every service. One ecosystem.</h1>
      <p>OrvenCore is the central platform for Karlo's apps, tools, APIs, and connected services. Sign in once, manage your account, connect Discord, and access the ecosystem from one place.</p>
    </div>
    <div class="actions">${cta}<a class="button" href="/apps" data-link>Explore Apps</a></div>
  </section>
  <section class="section">
    <p class="eyebrow">What OrvenCore Does</p>
    <div class="grid">
      ${[
        ["Central Authentication", "One OrvenCore account for all supported apps and services."],
        ["Discord Integration", "Connect Discord and use OrvenCore identity inside the Discord bot."],
        ["App Launcher", "Access FlashbackVHS, ProgressiveNodeX, OrvenTerminal, KPass, and future services."],
        ["Permissions & Roles", "Use central roles and permissions instead of rebuilding auth in every app."],
        ["Developer Platform", "APIs and service keys allow trusted apps and bots to communicate with OrvenCore."],
        ["Future SSO", "The platform is shaped to become the identity provider for the whole ecosystem."],
      ].map(([title, body]) => `<article class="card"><h3>${title}</h3><p>${body}</p></article>`).join("")}
    </div>
  </section>
  <section class="section">
    <p class="eyebrow">Ecosystem Preview</p>
    ${serviceCards(state.services)}
  </section>
  <section class="section panel">
    <h2>Why it exists</h2>
    <p>OrvenCore exists so every project does not need to rebuild accounts, permissions, login pages, Discord linking, and admin tools from scratch. It is the shared foundation for the entire ecosystem.</p>
    <div class="actions">${cta}<a class="button" href="/dashboard" data-link>Open Dashboard</a></div>
  </section>`;
}

function authView(mode) {
  const isLogin = mode === "login";
  return `<section class="form-panel">
    <p class="eyebrow">${isLogin ? "Welcome back" : "Create account"}</p>
    <h1>${isLogin ? "Log in to OrvenCore" : "Join OrvenCore"}</h1>
    <form class="form" id="auth-form">
      ${isLogin ? "" : `<label>Username<input name="username" minlength="3" required autocomplete="username"></label>
      <label>Display name<input name="display_name" autocomplete="name"></label>`}
      <label>${isLogin ? "Username or email" : "Email"}<input name="${isLogin ? "username_or_email" : "email"}" ${isLogin ? "" : "type=\"email\""} required></label>
      <label>Password<input name="password" type="password" minlength="${isLogin ? "1" : "10"}" required></label>
      <button class="button primary" type="submit">${isLogin ? "Log In" : "Create Account"}</button>
    </form>
    <p class="muted">${isLogin ? "Need an account?" : "Already have an account?"}
      <a href="${preserveDiscord(isLogin ? "/register" : "/login")}" data-link>${isLogin ? "Register" : "Log in"}</a>
    </p>
  </section>`;
}

function dashboardView() {
  if (!state.account) return authRequired();
  return `<section class="layout">
    <div class="panel">
      <p class="eyebrow">OrvenCore Home</p>
      <h1>${state.account.display_name || state.account.username}</h1>
      <p>${state.account.email}</p>
      <div class="section">
        <span class="status">${state.account.is_active ? "Active account" : "Disabled account"}</span>
        <div class="pill-row">${state.roles.map((role) => `<span class="pill">${role}</span>`).join("")}</div>
      </div>
    </div>
    <div class="panel">
      <h2>Discord</h2>
      <p>${state.account.discord_account ? `Linked as ${state.account.discord_account.username}` : "Discord is not linked yet."}</p>
      <div class="section">
        <h2>Permissions</h2>
        <div class="pill-row">${state.permissions.map((p) => `<span class="pill">${p}</span>`).join("")}</div>
      </div>
    </div>
  </section>
  <section class="section">
    <p class="eyebrow">Quick Launch</p>
    ${serviceCards(state.serviceAccess, true)}
  </section>`;
}

function accountView() {
  if (!state.account) return authRequired();
  return `<section class="layout">
    <div class="panel">
      <p class="eyebrow">Account Settings</p>
      <h1>${state.account.username}</h1>
      <p>Email: ${state.account.email}</p>
      <p>Display name: ${state.account.display_name || "Not set"}</p>
      <p class="muted">Password changes are coming soon.</p>
      <div class="actions"><button class="button" id="logout-current">Logout current session</button><button class="button" id="logout-all">Logout all devices</button></div>
    </div>
    <div class="panel">
      <h2>Active Sessions</h2>
      <table class="table"><tbody>${state.sessions.map((session) => `<tr><td>${session.user_agent || "Unknown device"}</td><td>${new Date(session.created_at).toLocaleString()}</td><td>${session.revoked_at ? "Revoked" : "Active"}</td></tr>`).join("")}</tbody></table>
    </div>
  </section>`;
}

function appsView() {
  const services = state.account && state.serviceAccess.length ? state.serviceAccess : state.services;
  return `<section class="section">
    <p class="eyebrow">App Launcher</p>
    <h1>OrvenCore Apps & Services</h1>
    <p class="section-lede">${state.account ? "Your access is calculated by the backend from your roles and permissions." : "Log in to see access details for every service."}</p>
    ${serviceCards(services, Boolean(state.account))}
    ${state.account ? "" : `<div class="actions"><a class="button primary" href="/login" data-link>Log In</a></div>`}
  </section>`;
}

function adminView() {
  if (!state.account) return authRequired();
  if (!isAdmin()) return `<section class="panel"><p class="eyebrow danger">Access denied</p><h1>Admin permissions required.</h1></section>`;
  return `<section class="section">
    <p class="eyebrow">Admin</p>
    <h1>OrvenCore Control Center</h1>
    <div class="grid two">
      ${["Users", "Discord Links", "API / Service Keys", "Services", "Roles", "Permissions", "System Health"].map((item) => `<article class="card"><h3>${item}</h3><p>Available through protected admin API endpoints. Full management UI is the next layer.</p></article>`).join("")}
      <article class="card"><h3>API Docs</h3><p>Swagger documentation for internal endpoints.</p><a class="button" href="/docs">Open Docs</a></article>
    </div>
  </section>`;
}

function authRequired() {
  return `<section class="panel"><p class="eyebrow">Authentication required</p><h1>Log in to continue.</h1><div class="actions"><a class="button primary" href="${preserveDiscord("/login")}" data-link>Log In</a></div></section>`;
}

async function logout() {
  const refreshToken = localStorage.getItem(refreshKey);
  if (refreshToken) {
    await api("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {});
  }
  localStorage.removeItem(tokenKey);
  localStorage.removeItem(refreshKey);
  await refreshState();
  navigate("/");
}

async function logoutAll() {
  await api("/auth/logout-all", { method: "POST", body: "{}" });
  localStorage.removeItem(tokenKey);
  localStorage.removeItem(refreshKey);
  await refreshState();
  navigate("/");
}

function attachHandlers() {
  document.querySelectorAll("[data-link]").forEach((link) => {
    link.addEventListener("click", (event) => {
      const href = link.getAttribute("href");
      if (!href || href.startsWith("http") || href === "/docs") return;
      event.preventDefault();
      navigate(href);
    });
  });

  document.querySelector("#auth-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const body = Object.fromEntries(new FormData(form).entries());
    try {
      if (window.location.pathname === "/register") {
        await api("/auth/register", { method: "POST", body: JSON.stringify(body) });
        body.username_or_email = body.username;
      }
      const tokens = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          username_or_email: body.username_or_email,
          password: body.password,
        }),
      });
      localStorage.setItem(tokenKey, tokens.access_token);
      localStorage.setItem(refreshKey, tokens.refresh_token);
      await refreshState();
      navigate("/dashboard");
    } catch (error) {
      showToast(error.message, "danger");
    }
  });

  document.querySelector("#logout-current")?.addEventListener("click", logout);
  document.querySelector("#logout-all")?.addEventListener("click", logoutAll);
}

async function render() {
  renderNav();
  const path = window.location.pathname;
  if (path === "/login") app.innerHTML = authView("login");
  else if (path === "/register") app.innerHTML = authView("register");
  else if (path === "/dashboard") app.innerHTML = dashboardView();
  else if (path === "/account") app.innerHTML = accountView();
  else if (path === "/apps") app.innerHTML = appsView();
  else if (path === "/admin") app.innerHTML = adminView();
  else app.innerHTML = homeView();
  attachHandlers();
}

window.addEventListener("popstate", render);

restoreSession()
  .then(render)
  .catch((error) => {
    app.innerHTML = `<section class="panel"><h1>OrvenCore could not load.</h1><p>${error.message}</p></section>`;
  });
