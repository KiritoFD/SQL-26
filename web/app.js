let session = null;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  window.setTimeout(() => node.classList.remove("show"), 2600);
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (session?.token) headers["X-Session-Token"] = session.token;
  const response = await fetch(path, { ...options, headers });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "请求失败");
  return payload;
}

function renderRows(target, rows, emptyText = "暂无数据") {
  const node = $(target);
  if (!rows || rows.length === 0) {
    node.innerHTML = `<div class="record">${emptyText}</div>`;
    return;
  }
  node.innerHTML = rows.map((row) => {
    const cells = Object.entries(row)
      .map(([key, value]) => `<div><b>${key}</b>：${value ?? ""}</div>`)
      .join("");
    return `<article class="record">${cells}</article>`;
  }).join("");
}

function setSession(nextSession) {
  session = nextSession;
  $("#sessionText").textContent = `${nextSession.role === "user" ? "用户" : "管理员"} ${nextSession.id} 已登录`;
  $("#userWorkspace").classList.toggle("hidden", nextSession.role !== "user");
  $("#adminWorkspace").classList.toggle("hidden", nextSession.role !== "admin");
}

function bindTabs() {
  $$(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      $$(".tab").forEach((item) => item.classList.remove("active"));
      $$(".tab-pane").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      $(`#${button.dataset.tab}`).classList.add("active");
    });
  });
}

function bindViews(scopeSelector) {
  $$(scopeSelector + " .side-nav button").forEach((button) => {
    button.addEventListener("click", () => {
      const scope = button.closest(".workspace");
      scope.querySelectorAll(".side-nav button").forEach((item) => item.classList.remove("active"));
      scope.querySelectorAll(".view").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      scope.querySelector(`#${button.dataset.view}`).classList.add("active");
    });
  });
}

function bindForms() {
  $("#initBtn").addEventListener("click", async () => {
    try {
      const result = await api("/api/init", { method: "POST", body: "{}" });
      toast(result.message);
    } catch (error) {
      toast(error.message);
    }
  });

  $("#userLogin").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      setSession(await api("/api/login/user", { method: "POST", body: JSON.stringify(formData(event.target)) }));
      toast("用户登录成功");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#adminLogin").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      setSession(await api("/api/login/admin", { method: "POST", body: JSON.stringify(formData(event.target)) }));
      toast("管理员登录成功");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#register").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const result = await api("/api/register", { method: "POST", body: JSON.stringify(formData(event.target)) });
      toast(result.message);
    } catch (error) {
      toast(error.message);
    }
  });

  $("#profileForm").addEventListener("submit", submitJson("PUT", "/api/profile", "个人信息已保存"));
  $("#adminProfileForm").addEventListener("submit", submitJson("PUT", "/api/admin/profile", "管理员信息已保存"));
  $("#addFriendForm").addEventListener("submit", submitJson("POST", "/api/friends", "好友已添加"));
  $("#groupForm").addEventListener("submit", submitJson("POST", "/api/groups", "分组已创建"));
  $("#moveFriendForm").addEventListener("submit", submitJson("PUT", "/api/friends/group", "分组已更新"));
  $("#momentForm").addEventListener("submit", submitJson("POST", "/api/moments", "朋友圈已发表"));
  $("#commentForm").addEventListener("submit", submitJson("POST", "/api/comments", "评论已发表"));

  $("#searchForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const keyword = encodeURIComponent(new FormData(event.target).get("keyword"));
      const result = await api(`/api/users/search?keyword=${keyword}`);
      renderRows("#friendOutput", result.data, "没有找到用户");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#editMomentForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.target);
    await action(() => api(`/api/moments/${data.moment_id}`, { method: "PUT", body: JSON.stringify({ content: data.content }) }), "朋友圈已修改");
  });

  $("#deleteMomentForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.target);
    await action(() => api(`/api/moments/${data.moment_id}`, { method: "DELETE", body: "{}" }), "朋友圈已删除");
  });

  $("#adminDeleteMomentForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.target);
    await action(() => api(`/api/admin/moments/${data.moment_id}`, { method: "DELETE", body: JSON.stringify({ reason: data.reason }) }), "朋友圈已审核删除");
  });

  $("#adminDisableUserForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.target);
    await action(() => api(`/api/admin/users/${data.user_id}`, { method: "DELETE", body: JSON.stringify({ reason: data.reason }) }), "用户已注销");
  });

  $("#loadCommentsForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const momentId = new FormData(event.target).get("moment_id");
    await load(`/api/comments?moment_id=${encodeURIComponent(momentId)}`, "#commentOutput", "暂无评论");
  });

  $("#refreshFriends").addEventListener("click", () => load("/api/friends", "#friendOutput", "暂无好友"));
  $("#loadMyMoments").addEventListener("click", () => load("/api/moments/my", "#momentOutput", "暂无朋友圈"));
  $("#loadFriendMoments").addEventListener("click", () => load("/api/moments/friends", "#momentOutput", "暂无好友朋友圈"));
  $("#loadAdminMoments").addEventListener("click", () => load("/api/admin/moments", "#adminMomentOutput", "暂无朋友圈"));
  $("#loadAuditLogs").addEventListener("click", () => load("/api/admin/audit-logs", "#auditOutput", "暂无审计日志"));
}

function submitJson(method, path, successText) {
  return async (event) => {
    event.preventDefault();
    await action(() => api(path, { method, body: JSON.stringify(formData(event.target)) }), successText);
  };
}

async function action(fn, successText) {
  try {
    await fn();
    toast(successText);
  } catch (error) {
    toast(error.message);
  }
}

async function load(path, target, emptyText) {
  try {
    const result = await api(path);
    renderRows(target, result.data, emptyText);
  } catch (error) {
    toast(error.message);
  }
}

bindTabs();
bindViews("#userWorkspace");
bindViews("#adminWorkspace");
bindForms();
