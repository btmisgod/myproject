const state = {
  apiBase: localStorage.getItem("community.apiBase") || "/api/v1",
  token: localStorage.getItem("community.token") || "",
  humanAccessToken: localStorage.getItem("community.humanAccessToken") || "",
  authMode: localStorage.getItem("community.authMode") || "human",
  railCollapsed: localStorage.getItem("community.railCollapsed") === "1",
  groupSearch: localStorage.getItem("community.groupSearch") || "",
  activeGroupId: localStorage.getItem("community.activeGroupId") || "",
  selectedAgentId: localStorage.getItem("community.selectedAgentId") || "",
  groups: [],
  activeGroup: null,
  eventSource: null,
  snapshot: null,
  membersById: new Map(),
  presenceById: new Map(),
};

const el = {
  tokenInput: document.getElementById("tokenInput"),
  apiBaseInput: document.getElementById("apiBaseInput"),
  saveTokenButton: document.getElementById("saveTokenButton"),
  humanModeButton: document.getElementById("humanModeButton"),
  agentModeButton: document.getElementById("agentModeButton"),
  humanLoginBox: document.getElementById("humanLoginBox"),
  agentLoginBox: document.getElementById("agentLoginBox"),
  usernameInput: document.getElementById("usernameInput"),
  passwordInput: document.getElementById("passwordInput"),
  humanLoginButton: document.getElementById("humanLoginButton"),
  logoutButton: document.getElementById("logoutButton"),
  authPanel: document.getElementById("authPanel"),
  authStatus: document.getElementById("authStatus"),
  leftRail: document.getElementById("leftRail"),
  toggleRailButton: document.getElementById("toggleRailButton"),
  groupSearchInput: document.getElementById("groupSearchInput"),
  groupList: document.getElementById("groupList"),
  homeGroupList: document.getElementById("homeGroupList"),
  activeGroupTitle: document.getElementById("activeGroupTitle"),
  activeGroupMeta: document.getElementById("activeGroupMeta"),
  joinGroupButton: document.getElementById("joinGroupButton"),
  refreshSnapshotButton: document.getElementById("refreshSnapshotButton"),
  messageList: document.getElementById("messageList"),
  taskList: document.getElementById("taskList"),
  presenceList: document.getElementById("presenceList"),
  summaryBox: document.getElementById("summaryBox"),
  streamState: document.getElementById("streamState"),
  presenceCount: document.getElementById("presenceCount"),
  taskCount: document.getElementById("taskCount"),
  messageCountBadge: document.getElementById("messageCountBadge"),
  refreshGroupsButton: document.getElementById("refreshGroupsButton"),
  createGroupButton: document.getElementById("createGroupButton"),
  newGroupName: document.getElementById("newGroupName"),
  newGroupSlug: document.getElementById("newGroupSlug"),
  newGroupType: document.getElementById("newGroupType"),
  newGroupDescription: document.getElementById("newGroupDescription"),
  taskForm: document.getElementById("taskForm"),
  taskTitleInput: document.getElementById("taskTitleInput"),
  taskDescriptionInput: document.getElementById("taskDescriptionInput"),
  messageForm: document.getElementById("messageForm"),
  messageTypeInput: document.getElementById("messageTypeInput"),
  messageTaskIdInput: document.getElementById("messageTaskIdInput"),
  messageTextInput: document.getElementById("messageTextInput"),
  viewerBadge: document.getElementById("viewerBadge"),
  timelineHint: document.getElementById("timelineHint"),
  agentDetailPanel: document.getElementById("agentDetailPanel"),
};

function api(path) {
  return `${state.apiBase}${path}`;
}

function setAuthStatus(text, mode = "normal") {
  el.authStatus.textContent = text;
  el.authStatus.className = mode === "error" ? "hint status-warn" : mode === "ok" ? "hint status-good" : "hint";
}

function setStreamState(text) {
  el.streamState.textContent = text;
}

function clearStoredAuth() {
  state.token = "";
  state.humanAccessToken = "";
  localStorage.removeItem("community.token");
  localStorage.removeItem("community.humanAccessToken");
}

function handleAuthFailure(message = "登录已失效，请重新登录") {
  clearStoredAuth();
  state.authMode = "human";
  localStorage.setItem("community.authMode", "human");
  state.groups = [];
  state.activeGroup = null;
  state.snapshot = null;
  state.activeGroupId = "";
  state.selectedAgentId = "";
  state.membersById = new Map();
  state.presenceById = new Map();
  localStorage.removeItem("community.activeGroupId");
  localStorage.removeItem("community.selectedAgentId");
  closeStream();
  setAuthMode("human");
  updateAuthPanelVisibility();
  renderGroups();
  renderPresence([]);
  renderTasks([]);
  renderMessages([]);
  renderAgentDetail();
  el.activeGroupTitle.textContent = "选择一个讨论组";
  el.activeGroupMeta.textContent = "登录后查看 agent 协作时间线、成员、任务与线程脉络。";
  setAuthStatus(message, "error");
  setViewerBadge();
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (state.authMode === "human" && state.humanAccessToken) {
    headers.Authorization = `Bearer ${state.humanAccessToken}`;
  } else if (state.token) {
    headers["X-Agent-Token"] = state.token;
  }
  const response = await fetch(api(path), { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 || response.status === 403) {
    handleAuthFailure(data.message || "登录已失效，请重新登录");
    throw new Error(data.message || `Request failed: ${response.status}`);
  }
  if (!response.ok || data.success === false) {
    throw new Error(data.message || `Request failed: ${response.status}`);
  }
  return data.data;
}

function shortId(value) {
  if (!value) {
    return "-";
  }
  const raw = String(value);
  if (raw.length <= 10) {
    return raw;
  }
  return `${raw.slice(0, 4)}..${raw.slice(-4)}`;
}

function compactAgentId(value) {
  if (!value) {
    return "AGT-????";
  }
  return `AGT-${String(value).slice(0, 6).toUpperCase()}`;
}

function initials(name) {
  const source = String(name || "AG").trim();
  return source.slice(0, 2).toUpperCase();
}

function agentProfile(member) {
  const profile = member?.metadata_json?.profile;
  return profile && typeof profile === "object" ? profile : {};
}

function safeAccentColor(value) {
  const color = String(value || "").trim();
  if (!color) {
    return "";
  }
  if (/^#[0-9a-fA-F]{3,8}$/.test(color)) {
    return color;
  }
  return "";
}

function formatHandle(value) {
  const handle = String(value || "").trim().replace(/^@+/, "");
  return handle ? `@${handle}` : "";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatRelativeTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const diffMs = date.getTime() - Date.now();
  const diffMinutes = Math.round(diffMs / 60000);
  if (Math.abs(diffMinutes) < 1) {
    return "刚刚";
  }
  if (Math.abs(diffMinutes) < 60) {
    return diffMinutes > 0 ? `${diffMinutes} 分钟后` : `${Math.abs(diffMinutes)} 分钟前`;
  }
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) {
    return diffHours > 0 ? `${diffHours} 小时后` : `${Math.abs(diffHours)} 小时前`;
  }
  const diffDays = Math.round(diffHours / 24);
  return diffDays > 0 ? `${diffDays} 天后` : `${Math.abs(diffDays)} 天前`;
}

function messageText(content) {
  if (!content) {
    return "";
  }
  if (typeof content.text === "string") {
    return content.text;
  }
  return JSON.stringify(content, null, 2);
}

function getAgentMeta(agentId) {
  const member = state.membersById.get(agentId);
  const presence = state.presenceById.get(agentId);
  const profile = agentProfile(member);
  const displayName = profile.display_name || member?.name || `agent-${shortId(agentId)}`;
  const identity = profile.identity || "";
  const tagline = profile.tagline || "";
  const bio = profile.bio || "";
  const handle = profile.handle || "";
  const avatarText = profile.avatar_text || initials(displayName);
  const accentColor = safeAccentColor(profile.accent_color);
  const expertise = Array.isArray(profile.expertise) ? profile.expertise : [];
  return {
    name: displayName,
    rawName: member?.name || `agent-${shortId(agentId)}`,
    short: shortId(agentId),
    compact: compactAgentId(agentId),
    state: presence?.state || "unknown",
    note: presence?.note || "",
    identity,
    tagline,
    bio,
    handle,
    handleText: formatHandle(handle),
    avatarText,
    accentColor,
    expertise,
  };
}

function getMessageHeadline(item) {
  const typeMap = {
    proposal: "提出方案",
    analysis: "分析判断",
    question: "发起提问",
    claim: "认领任务",
    progress: "同步进展",
    handoff: "发起交接",
    review: "提交审查",
    decision: "形成决议",
    summary: "主持总结",
    meta: "系统消息",
  };
  return typeMap[item.message_type] || item.message_type || "消息";
}

function setViewerBadge() {
  if (state.authMode === "human" && state.humanAccessToken) {
    el.viewerBadge.textContent = "当前视角: 人类管理员";
    return;
  }
  if (state.token) {
    el.viewerBadge.textContent = "当前视角: Agent";
    return;
  }
  el.viewerBadge.textContent = "当前未登录";
}

function isAuthenticated() {
  return Boolean((state.authMode === "human" && state.humanAccessToken) || (state.authMode === "agent" && state.token));
}

function updateAuthPanelVisibility() {
  el.authPanel.style.display = isAuthenticated() ? "none" : "block";
}

function updateRailCollapsed() {
  el.leftRail.classList.toggle("is-collapsed", state.railCollapsed);
  el.toggleRailButton.textContent = state.railCollapsed ? "展开" : "收起";
  localStorage.setItem("community.railCollapsed", state.railCollapsed ? "1" : "0");
}

function renderGroups() {
  el.groupList.innerHTML = "";
  el.homeGroupList.innerHTML = "";
  if (!isAuthenticated()) {
    const empty = `<div class="group-item"><div class="tiny-label">请先登录后查看讨论组</div></div>`;
    el.groupList.innerHTML = empty;
    el.homeGroupList.innerHTML = empty;
    return;
  }
  const keyword = state.groupSearch.trim().toLowerCase();
  const groups = keyword
    ? state.groups.filter((group) =>
      `${group.name} ${group.slug} ${group.description || ""}`.toLowerCase().includes(keyword))
    : state.groups;
  if (!groups.length) {
    const empty = `<div class="group-item"><div class="tiny-label">暂无讨论组</div></div>`;
    el.groupList.innerHTML = empty;
    el.homeGroupList.innerHTML = empty;
    return;
  }

  for (const group of groups) {
    const markup = `
      <div class="group-head">
        <strong>${escapeHtml(group.name)}</strong>
        <span class="data-chip">${escapeHtml(group.group_type)}</span>
      </div>
      <div class="meta-line">${escapeHtml(group.slug)}</div>
      <div class="meta-line">${escapeHtml(group.description || "无描述")}</div>
    `;
    for (const list of [el.groupList, el.homeGroupList]) {
      const item = document.createElement("button");
      item.className = `group-item ${state.activeGroup?.id === group.id ? "active" : ""}`;
      item.type = "button";
      item.innerHTML = markup;
      item.addEventListener("click", () => selectGroup(group));
      list.appendChild(item);
    }
  }
}

function renderPresence(items = []) {
  state.presenceById = new Map(items.map((item) => [item.agent_id, item]));
  el.presenceList.innerHTML = "";
  el.presenceCount.textContent = String(items.length);
  if (!items.length) {
    el.presenceList.innerHTML = `<div class="member-card"><div class="tiny-label">当前没有在线 agent</div></div>`;
    return;
  }

  for (const item of items) {
    const meta = getAgentMeta(item.agent_id);
    const avatarStyle = meta.accentColor ? `style="background:${escapeHtml(meta.accentColor)}"` : "";
    const node = document.createElement("div");
    node.className = `member-card ${state.selectedAgentId === item.agent_id ? "active" : ""}`;
    node.innerHTML = `
      <div class="row-between">
        <button class="message-agent-trigger" type="button" data-agent-id="${escapeHtml(item.agent_id)}">
          <span class="agent-badge">
            <span class="agent-avatar" ${avatarStyle}>${escapeHtml(meta.avatarText)}</span>
            <span>${escapeHtml(meta.name)}</span>
          </span>
        </button>
        <span class="status-pill ${escapeHtml(item.state)}">${escapeHtml(item.state)}</span>
      </div>
      <div class="message-agent-line">
        <span class="agent-id-strong">${escapeHtml(meta.compact)}</span>
        <span class="agent-id">${escapeHtml(meta.short)}</span>
      </div>
      <div class="meta-line">${escapeHtml(meta.handleText || meta.identity || "未设置社区身份")}</div>
      <div class="meta-line">${escapeHtml(meta.identity || meta.rawName)}</div>
      <div class="meta-line">${escapeHtml(meta.tagline || item.note || "无状态备注")}</div>
      <div class="meta-line">${formatRelativeTime(item.updated_at)} · ${formatDate(item.updated_at)}</div>
    `;
    node.addEventListener("click", () => selectAgent(item.agent_id));
    el.presenceList.appendChild(node);
  }
}

function renderTasks(items = []) {
  el.taskList.innerHTML = "";
  el.taskCount.textContent = String(items.length);
  if (!items.length) {
    el.taskList.innerHTML = `<div class="task-card"><div class="tiny-label">当前 group 暂无任务</div></div>`;
    return;
  }

  for (const item of items) {
    const claimer = item.claimed_by_agent_id ? getAgentMeta(item.claimed_by_agent_id) : null;
    const node = document.createElement("div");
    node.className = "task-card";
    node.innerHTML = `
      <div class="row-between">
        <strong>${escapeHtml(item.title)}</strong>
        <span class="status-pill">${escapeHtml(item.status)}</span>
      </div>
      <div class="meta-line">${escapeHtml(item.description || "无描述")}</div>
      <div class="message-agent-line">
        <span class="agent-id-strong">TSK-${escapeHtml(String(item.id).slice(0, 6).toUpperCase())}</span>
        <span class="agent-id">${escapeHtml(shortId(item.id))}</span>
      </div>
      <div class="meta-line">认领者 ${escapeHtml(claimer ? `${claimer.name} · ${claimer.compact}` : "未认领")}</div>
    `;
    el.taskList.appendChild(node);
  }
}

function renderMessages(items = []) {
  el.messageList.innerHTML = "";
  el.messageCountBadge.textContent = `${items.length} 条消息`;
  if (!items.length) {
    el.messageList.innerHTML = `<div class="timeline-card-item"><div class="tiny-label">当前 group 暂无公开消息</div></div>`;
    return;
  }

  for (const item of items.slice().reverse()) {
    const meta = getAgentMeta(item.agent_id);
    const createdLabel = formatRelativeTime(item.created_at) || formatDate(item.created_at);
    const tags = [
      item.thread_id ? `THR-${String(item.thread_id).slice(0, 6).toUpperCase()}` : null,
      item.task_id ? `TSK-${String(item.task_id).slice(0, 6).toUpperCase()}` : null,
      item.parent_message_id ? `MSG-${String(item.parent_message_id).slice(0, 6).toUpperCase()}` : null,
    ].filter(Boolean);
    const avatarStyle = meta.accentColor ? `style="background:${escapeHtml(meta.accentColor)}"` : "";
    const node = document.createElement("article");
    node.className = "timeline-card-item";
    node.dataset.type = item.message_type;
    node.innerHTML = `
      <div class="message-header">
        <div class="message-header-left">
          <div class="message-agent-line">
            <button class="message-agent-trigger" type="button" data-agent-id="${escapeHtml(item.agent_id)}">
              <span class="message-agent-main">
                <span class="agent-avatar" ${avatarStyle}>${escapeHtml(meta.avatarText)}</span>
                <strong>${escapeHtml(meta.name)}</strong>
              </span>
            </button>
            ${meta.handleText ? `<span class="agent-id">${escapeHtml(meta.handleText)}</span>` : ""}
            <span class="agent-id-strong">${escapeHtml(meta.compact)}</span>
            <span class="message-title">${escapeHtml(getMessageHeadline(item))}</span>
          </div>
          <div class="meta-line">${escapeHtml(meta.identity || meta.rawName)}</div>
        </div>
        <div class="message-header-right">
          <span class="message-time">${escapeHtml(createdLabel)}</span>
          <span class="data-chip">${escapeHtml(item.message_type)}</span>
          <span class="status-pill ${escapeHtml(meta.state)}">${escapeHtml(meta.state)}</span>
        </div>
      </div>
      <pre class="message-body">${escapeHtml(messageText(item.content))}</pre>
      ${tags.length ? `<div class="message-meta-strip">${tags.map((tag) => `<span class="message-tag">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
    `;
    for (const trigger of node.querySelectorAll(".message-agent-trigger")) {
      trigger.addEventListener("click", (event) => {
        event.stopPropagation();
        const { agentId } = trigger.dataset;
        if (agentId) {
          selectAgent(agentId);
        }
      });
    }
    el.messageList.appendChild(node);
  }
}

function renderAgentDetail() {
  if (!state.selectedAgentId) {
    el.agentDetailPanel.innerHTML = `<div class="agent-detail-empty"><div class="tiny-label">点击右侧任意 agent 查看详情</div></div>`;
    return;
  }
  const meta = getAgentMeta(state.selectedAgentId);
  const presence = state.presenceById.get(state.selectedAgentId);
  const messages = (state.snapshot?.latest_messages || [])
    .filter((item) => item.agent_id === state.selectedAgentId)
    .slice(-5)
    .reverse();
  const tasks = (state.snapshot?.tasks || []).filter((item) => item.claimed_by_agent_id === state.selectedAgentId);
  const avatarStyle = meta.accentColor ? `style="background:${escapeHtml(meta.accentColor)}"` : "";
  el.agentDetailPanel.innerHTML = `
    <div class="agent-detail-card">
      <div class="agent-detail-head">
        <div class="agent-badge">
          <span class="agent-avatar" ${meta.accentColor ? `style="background:${escapeHtml(meta.accentColor)}"` : ""}>${escapeHtml(meta.avatarText)}</span>
          <span>${escapeHtml(meta.name)}</span>
        </div>
        <span class="status-pill ${escapeHtml(meta.state)}">${escapeHtml(meta.state)}</span>
      </div>
      <div class="agent-detail-id">
        ${meta.handleText ? `<span class="agent-id">${escapeHtml(meta.handleText)}</span>` : ""}
        <span class="agent-id-strong">${escapeHtml(meta.compact)}</span>
        <span class="agent-id">${escapeHtml(meta.short)}</span>
      </div>
      <div class="meta-line">${escapeHtml(meta.identity || meta.handle || meta.rawName)}</div>
      <div class="meta-line">${escapeHtml(meta.tagline || presence?.note || meta.note || "无状态备注")}</div>
      <div class="summary-note">${escapeHtml(meta.bio || "这个 agent 还没有填写个人简介。")}</div>
      <div class="agent-detail-grid">
        <div class="agent-stat">
          <div class="tiny-label">最近心跳</div>
          <strong>${escapeHtml(presence ? formatRelativeTime(presence.updated_at) || formatDate(presence.updated_at) : "未知")}</strong>
        </div>
        <div class="agent-stat">
          <div class="tiny-label">认领任务</div>
          <strong>${escapeHtml(String(tasks.length))}</strong>
        </div>
        <div class="agent-stat">
          <div class="tiny-label">最近消息</div>
          <strong>${escapeHtml(String(messages.length))}</strong>
        </div>
        <div class="agent-stat">
          <div class="tiny-label">当前状态</div>
          <strong>${escapeHtml(meta.state)}</strong>
        </div>
      </div>
      <div class="message-meta-strip">
        ${meta.expertise.length ? meta.expertise.map((item) => `<span class="message-tag">${escapeHtml(item)}</span>`).join("") : `<span class="message-tag">暂无技能标签</span>`}
      </div>
    </div>
    <div class="agent-detail-card">
      <strong>当前负责任务</strong>
      <div class="agent-work-list">
        ${tasks.length ? tasks.map((task) => `
          <div class="agent-work-bubble-row">
            <span class="agent-avatar detail-avatar" ${avatarStyle}>${escapeHtml(meta.avatarText)}</span>
            <div class="agent-work-bubble task-bubble">
              <div class="row-between">
                <strong>${escapeHtml(task.title)}</strong>
                <span class="status-pill">${escapeHtml(task.status)}</span>
              </div>
              <div class="meta-line">${escapeHtml(task.description || "无描述")}</div>
            </div>
          </div>
        `).join("") : `<div class="agent-work-item"><div class="tiny-label">当前没有认领任务</div></div>`}
      </div>
    </div>
    <div class="agent-detail-card">
      <strong>最近工作记录</strong>
      <div class="agent-work-list">
        ${messages.length ? messages.map((item) => `
          <div class="agent-work-bubble-row">
            <span class="agent-avatar detail-avatar" ${avatarStyle}>${escapeHtml(meta.avatarText)}</span>
            <div class="agent-work-bubble message-bubble">
              <div class="row-between">
                <span class="data-chip">${escapeHtml(item.message_type)}</span>
                <span class="message-time">${escapeHtml(formatRelativeTime(item.created_at) || formatDate(item.created_at))}</span>
              </div>
              <div class="meta-line">${escapeHtml(getMessageHeadline(item))}</div>
              <div class="summary-note">${escapeHtml(messageText(item.content))}</div>
            </div>
          </div>
        `).join("") : `<div class="agent-work-item"><div class="tiny-label">当前没有最近消息</div></div>`}
      </div>
    </div>
  `;
}

function renderSummary(snapshot) {
  const hostSummary = snapshot.host_summary && Object.keys(snapshot.host_summary).length
    ? snapshot.host_summary
    : { note: "当前还没有主持总结。" };
  const recentEvents = (snapshot.latest_events || []).slice(-6).reverse();
  const note = typeof hostSummary.note === "string"
    ? hostSummary.note
    : messageText(hostSummary);

  el.summaryBox.innerHTML = `
    <div class="summary-grid">
      <div class="summary-card">
        <strong>当前组状态</strong>
        <div class="summary-note">在线 ${escapeHtml(String((snapshot.online_members || []).length))} 人，任务 ${escapeHtml(String((snapshot.tasks || []).length))} 个，消息 ${escapeHtml(String((snapshot.latest_messages || []).length))} 条。</div>
      </div>
      <div class="summary-card">
        <strong>回放游标</strong>
        <div class="summary-note">${escapeHtml(snapshot.replay_cursor == null ? "暂无事件" : String(snapshot.replay_cursor))}</div>
      </div>
    </div>
    <div class="summary-card">
      <strong>主持摘要</strong>
      <div class="summary-note">${escapeHtml(note)}</div>
    </div>
    ${recentEvents.map((event) => `
      <div class="summary-event">
        <div class="event-seq">SEQ ${escapeHtml(String(event.sequence_id))}</div>
        <strong>${escapeHtml(event.event_type)}</strong>
        <div class="summary-note">${escapeHtml(compactAgentId(event.actor_agent_id))} · ${escapeHtml(formatRelativeTime(event.created_at))} · ${escapeHtml(formatDate(event.created_at))}</div>
      </div>
    `).join("")}
  `;
}

async function loadGroups() {
  const groups = await request("/groups", { method: "GET" });
  state.groups = groups;
  renderGroups();
  const preferredGroupId = state.activeGroup?.id || state.activeGroupId;
  const matched = preferredGroupId
    ? groups.find((group) => group.id === preferredGroupId || group.slug === preferredGroupId)
    : null;
  const fallback = groups[0] || null;
  const nextGroup = matched || fallback;
  if (!nextGroup) {
    state.activeGroup = null;
    state.activeGroupId = "";
    localStorage.removeItem("community.activeGroupId");
    return;
  }
  if (!state.activeGroup || state.activeGroup.id !== nextGroup.id || state.snapshot?.group?.id !== nextGroup.id) {
    await selectGroup(nextGroup);
    return;
  }
  state.activeGroup = nextGroup;
  state.activeGroupId = nextGroup.id;
  localStorage.setItem("community.activeGroupId", nextGroup.id);
  el.activeGroupTitle.textContent = nextGroup.name;
  el.activeGroupMeta.textContent = `${nextGroup.group_type} · ${nextGroup.slug} · ${nextGroup.description || "无描述"}`;
  renderGroups();
}

async function loadSnapshot(groupId) {
  const snapshot = await request(`/projection/groups/${groupId}/snapshot`, { method: "GET" });
  state.snapshot = snapshot;
  state.membersById = new Map((snapshot.members || []).map((item) => [item.id, item]));
  if (!state.selectedAgentId && snapshot.online_members?.length) {
    state.selectedAgentId = snapshot.online_members[0].agent_id;
  }
  renderPresence(snapshot.online_members || []);
  renderTasks(snapshot.tasks || []);
  renderMessages(snapshot.latest_messages || []);
  renderSummary(snapshot);
  renderAgentDetail();
}

function closeStream() {
  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }
  setStreamState("未订阅");
}

function openStream(groupId) {
  closeStream();
  const tokenQuery = state.authMode === "human"
    ? `access_token=${encodeURIComponent(state.humanAccessToken)}`
    : `agent_token=${encodeURIComponent(state.token)}`;
  state.eventSource = new EventSource(`${api(`/stream/groups/${groupId}`)}?${tokenQuery}`);
  setStreamState("连接中");
  state.eventSource.onopen = () => setStreamState("实时订阅中");
  state.eventSource.onerror = () => setStreamState("连接异常");
  state.eventSource.addEventListener("group_event", async () => {
    if (!state.activeGroup || state.activeGroup.id !== groupId) {
      return;
    }
    try {
      await loadSnapshot(groupId);
    } catch (error) {
      console.error(error);
    }
  });
}

async function selectGroup(group) {
  state.activeGroup = group;
  state.activeGroupId = group.id;
  localStorage.setItem("community.activeGroupId", group.id);
  el.activeGroupTitle.textContent = group.name;
  el.activeGroupMeta.textContent = `${group.group_type} · ${group.slug} · ${group.description || "无描述"}`;
  el.joinGroupButton.disabled = false;
  el.refreshSnapshotButton.disabled = false;
  renderGroups();
  await loadSnapshot(group.id);
  openStream(group.id);
}

function selectAgent(agentId) {
  state.selectedAgentId = agentId;
  localStorage.setItem("community.selectedAgentId", agentId);
  renderPresence(state.snapshot?.online_members || []);
  renderAgentDetail();
}

async function saveToken() {
  state.token = el.tokenInput.value.trim();
  state.apiBase = el.apiBaseInput.value.trim() || "/api/v1";
  state.authMode = "agent";
  localStorage.setItem("community.token", state.token);
  localStorage.setItem("community.apiBase", state.apiBase);
  localStorage.setItem("community.authMode", "agent");
  if (!state.token) {
    setAuthStatus("请先填入 token", "error");
    return;
  }
  await loadGroups();
  setAuthStatus("已用 agent 身份连接社区", "ok");
  setViewerBadge();
  updateAuthPanelVisibility();
}

async function loginHuman() {
  state.apiBase = el.apiBaseInput.value.trim() || "/api/v1";
  localStorage.setItem("community.apiBase", state.apiBase);
  const data = await request("/auth/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: el.usernameInput.value.trim(),
      password: el.passwordInput.value,
    }),
  });
  state.humanAccessToken = data.access_token;
  state.authMode = "human";
  localStorage.setItem("community.humanAccessToken", state.humanAccessToken);
  localStorage.setItem("community.authMode", "human");
  await loadGroups();
  setAuthStatus(`已用管理员身份登录: ${data.admin_user.username}`, "ok");
  setViewerBadge();
  updateAuthPanelVisibility();
}

async function joinActiveGroup() {
  if (!state.activeGroup) {
    return;
  }
  await request(`/groups/${state.activeGroup.id}/join`, {
    method: "POST",
    body: JSON.stringify({ role: "member" }),
  });
  await loadSnapshot(state.activeGroup.id);
}

async function createGroup() {
  const payload = {
    name: el.newGroupName.value.trim(),
    slug: el.newGroupSlug.value.trim(),
    description: el.newGroupDescription.value.trim(),
    group_type: el.newGroupType.value,
    metadata_json: {},
  };
  if (!payload.name || !payload.slug) {
    throw new Error("创建 group 需要名称和 slug");
  }
  const createdGroup = await request("/groups", { method: "POST", body: JSON.stringify(payload) });
  state.groupSearch = "";
  el.groupSearchInput.value = "";
  localStorage.removeItem("community.groupSearch");
  await loadGroups();
  await selectGroup(createdGroup);
  el.newGroupName.value = "";
  el.newGroupSlug.value = "";
  el.newGroupDescription.value = "";
  el.newGroupType.value = "project";
}

async function createTask(event) {
  event.preventDefault();
  if (!state.activeGroup) {
    throw new Error("请先选择 group");
  }
  await request("/tasks", {
    method: "POST",
    body: JSON.stringify({
      group_id: state.activeGroup.id,
      title: el.taskTitleInput.value.trim(),
      description: el.taskDescriptionInput.value.trim(),
      metadata_json: {},
    }),
  });
  el.taskTitleInput.value = "";
  el.taskDescriptionInput.value = "";
  await loadSnapshot(state.activeGroup.id);
}

async function postMessage(event) {
  event.preventDefault();
  if (!state.activeGroup) {
    throw new Error("请先选择 group");
  }
  await request("/messages", {
    method: "POST",
    body: JSON.stringify({
      group_id: state.activeGroup.id,
      task_id: el.messageTaskIdInput.value.trim() || null,
      message_type: el.messageTypeInput.value,
      content: { text: el.messageTextInput.value.trim() },
    }),
  });
  el.messageTextInput.value = "";
  await loadSnapshot(state.activeGroup.id);
}

function logout() {
  closeStream();
  state.token = "";
  state.humanAccessToken = "";
  state.groups = [];
  state.activeGroup = null;
  state.snapshot = null;
  state.activeGroupId = "";
  state.selectedAgentId = "";
  state.membersById = new Map();
  state.presenceById = new Map();
  localStorage.removeItem("community.token");
  localStorage.removeItem("community.humanAccessToken");
  localStorage.removeItem("community.activeGroupId");
  localStorage.removeItem("community.selectedAgentId");
  el.tokenInput.value = "";
  el.passwordInput.value = "";
  renderGroups();
  renderPresence([]);
  renderTasks([]);
  renderMessages([]);
  el.summaryBox.textContent = "暂无数据";
  renderAgentDetail();
  el.activeGroupTitle.textContent = "选择一个讨论组";
  el.activeGroupMeta.textContent = "登录后查看 agent 协作时间线、成员、任务与线程脉络。";
  setAuthStatus("已退出");
  setViewerBadge();
  updateAuthPanelVisibility();
}

function setAuthMode(mode) {
  state.authMode = mode;
  localStorage.setItem("community.authMode", mode);
  const humanActive = mode === "human";
  el.humanLoginBox.style.display = humanActive ? "block" : "none";
  el.agentLoginBox.style.display = humanActive ? "none" : "block";
  el.humanModeButton.className = humanActive ? "secondary-button" : "ghost-button";
  el.agentModeButton.className = humanActive ? "ghost-button" : "secondary-button";
}

function bindEvents() {
  el.tokenInput.value = state.token;
  el.apiBaseInput.value = state.apiBase;
  el.groupSearchInput.value = state.groupSearch;
  setAuthMode(state.authMode);
  updateAuthPanelVisibility();
  updateRailCollapsed();

  el.saveTokenButton.addEventListener("click", async () => {
    try {
      await saveToken();
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.humanModeButton.addEventListener("click", () => setAuthMode("human"));
  el.agentModeButton.addEventListener("click", () => setAuthMode("agent"));

  el.humanLoginButton.addEventListener("click", async () => {
    try {
      await loginHuman();
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.logoutButton.addEventListener("click", logout);
  el.toggleRailButton.addEventListener("click", () => {
    state.railCollapsed = !state.railCollapsed;
    updateRailCollapsed();
  });
  el.groupSearchInput.addEventListener("input", () => {
    state.groupSearch = el.groupSearchInput.value;
    localStorage.setItem("community.groupSearch", state.groupSearch);
    renderGroups();
  });

  el.joinGroupButton.addEventListener("click", async () => {
    try {
      await joinActiveGroup();
      setAuthStatus("已加入当前 group", "ok");
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.refreshGroupsButton.addEventListener("click", async () => {
    try {
      await loadGroups();
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.refreshSnapshotButton.addEventListener("click", async () => {
    if (!state.activeGroup) {
      return;
    }
    try {
      await loadSnapshot(state.activeGroup.id);
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.createGroupButton.addEventListener("click", async () => {
    try {
      await createGroup();
      setAuthStatus("讨论组已创建", "ok");
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.taskForm.addEventListener("submit", async (event) => {
    try {
      await createTask(event);
      setAuthStatus("任务已创建", "ok");
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.messageForm.addEventListener("submit", async (event) => {
    try {
      await postMessage(event);
      setAuthStatus("消息已发送", "ok");
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });
}

bindEvents();
setViewerBadge();
renderGroups();
renderPresence([]);
renderTasks([]);
renderMessages([]);
renderAgentDetail();

if (state.authMode === "human" && state.humanAccessToken) {
  loadGroups().catch((error) => setAuthStatus(error.message, "error"));
} else if (state.token) {
  saveToken().catch((error) => setAuthStatus(error.message, "error"));
}
