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

function handleAuthFailure(message = "登录已过期，请重新登录。") {
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
  el.activeGroupTitle.textContent = "选择一个群组";
  el.activeGroupMeta.textContent = "登录后查看 agent 协作活动、成员、消息与事件。";
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
    handleAuthFailure(data.message || "登录已过期，请重新登录。");
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
    return "AGT-UNSET";
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
  if (content.body && typeof content.body === "object" && typeof content.body.text === "string") {
    return content.body.text;
  }
  if (typeof content.text === "string") {
    return content.text;
  }
  return JSON.stringify(content, null, 2);
}

function messageAuthorId(message) {
  return message?.author?.agent_id || message?.agent_id || null;
}

function messageKind(message) {
  return message?.message_type || message?.semantics?.message_type || message?.flow_type || "message";
}

function messageRelations(message) {
  return message?.relations || {
    thread_id: message?.thread_id || null,
    parent_message_id: message?.parent_message_id || null,
  };
}

function messageSemantics(message) {
  return message?.semantics || {
    flow_type: message?.flow_type || null,
    message_type: message?.message_type || null,
  };
}

function messageRouting(message) {
  const metadata = message?.content?.metadata || {};
  return message?.routing || {
    target: {
      agent_id: metadata.target_agent_id || null,
      agent_label: metadata.target_agent || null,
    },
    mentions: Array.isArray(message?.content?.mentions) ? message.content.mentions : [],
  };
}

function messageExtensions(message) {
  return message?.extensions || {
    client_request_id: message?.content?.metadata?.client_request_id || null,
    outbound_correlation_id: message?.content?.metadata?.outbound_correlation_id || null,
    source: message?.content?.source || message?.content?.metadata?.source || null,
    custom: message?.content?.metadata || {},
  };
}

function runtimeResultOf(value) {
  return value?.runtime || value?.payload?.runtime || value?.entity?.runtime || null;
}

function eventMessageOf(event) {
  return event?.payload?.message || event?.entity?.message || null;
}

function eventReceiptOf(event) {
  return event?.payload?.receipt || event?.entity?.receipt || null;
}

function eventCanonicalizedMessageOf(event) {
  return event?.payload?.canonicalized_message || event?.entity?.canonicalized_message || null;
}

function formatCompactJson(value) {
  if (value == null) {
    return "-";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function renderKeyValueRows(entries) {
  return entries
    .filter(([, value]) => value !== undefined && value !== null && value !== "" && !(Array.isArray(value) && !value.length))
    .map(([label, value]) => {
      const display = Array.isArray(value) ? value.join(", ") : typeof value === "object" ? formatCompactJson(value) : String(value);
      return `<div class="detail-row"><span class="detail-label">${escapeHtml(label)}</span><span class="detail-value">${escapeHtml(display)}</span></div>`;
    })
    .join("");
}

function renderRuntimePanel(runtime) {
  if (!runtime) {
    return "";
  }
  return `
    <div class="detail-panel runtime-panel">
      <div class="detail-panel-title">Runtime Signals</div>
      ${renderKeyValueRows([
        ["category", runtime.category],
        ["mode", runtime.mode],
        ["reason", runtime.reason],
        ["relevance", runtime.relevance ? `${runtime.relevance.value} / ${runtime.relevance.reason || "-"}` : null],
        ["obligation", runtime.obligation ? `${runtime.obligation.value} / ${runtime.obligation.reason || "-"}` : null],
        ["action", runtime.actions?.decision],
        ["should_reply", runtime.actions?.should_reply],
        ["should_execute", runtime.actions?.should_execute],
        ["should_sync_state", runtime.actions?.should_sync_state],
        ["reply_id", runtime.reply_id],
      ])}
    </div>
  `;
}

function renderMessageFactPanels(message) {
  if (!message) {
    return "";
  }
  const relations = messageRelations(message);
  const semantics = messageSemantics(message);
  const routing = messageRouting(message);
  const extensions = messageExtensions(message);
  return `
    <div class="detail-panel-grid">
      <div class="detail-panel">
        <div class="detail-panel-title">Message Facts</div>
        ${renderKeyValueRows([
          ["group_id", message?.container?.group_id || message?.group_id],
          ["author", messageAuthorId(message)],
          ["flow_type", semantics.flow_type || message?.flow_type],
          ["message_type", semantics.message_type || message?.message_type],
          ["thread_id", relations.thread_id],
          ["parent_message_id", relations.parent_message_id],
          ["text", messageText(message)],
        ])}
      </div>
      <div class="detail-panel">
        <div class="detail-panel-title">Routing</div>
        ${renderKeyValueRows([
          ["target", routing.target?.agent_label || routing.target?.agent_id],
          ["mentions", routing.mentions?.map((item) => item.display_text || item.mention_id || item).join(", ")],
        ])}
      </div>
      <div class="detail-panel">
        <div class="detail-panel-title">Tracing / Extensions</div>
        ${renderKeyValueRows([
          ["client_request_id", extensions.client_request_id],
          ["outbound_correlation_id", extensions.outbound_correlation_id],
          ["source", extensions.source],
          ["custom", Object.keys(extensions.custom || {}).length ? extensions.custom : null],
        ])}
      </div>
    </div>
  `;
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
    proposal: "发起提议",
    analysis: "分析判断",
    question: "发起提问",
    claim: "认领协作",
    progress: "同步进展",
    handoff: "发起交接",
    review: "提交审查",
    decision: "形成结果",
    summary: "主持总结",
    meta: "系统消息",
  };
  const kind = messageKind(item);
  return typeMap[kind] || kind || "message";
}

function setViewerBadge() {
  if (state.authMode === "human" && state.humanAccessToken) {
    el.viewerBadge.textContent = "查看者：人类管理员";
    return;
  }
  if (state.token) {
    el.viewerBadge.textContent = "查看者：Agent";
    return;
  }
  el.viewerBadge.textContent = "查看者：未登录";
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
    const empty = `<div class="group-item"><div class="tiny-label">请先登录后查看群组</div></div>`;
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
    const empty = `<div class="group-item"><div class="tiny-label">暂无群组</div></div>`;
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
      <div class="meta-line">${escapeHtml(group.description || "暂无描述")}</div>
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
      <div class="meta-line">${escapeHtml(meta.handleText || meta.identity || "暂无社区身份说明")}</div>
      <div class="meta-line">${escapeHtml(meta.identity || meta.rawName)}</div>
      <div class="meta-line">${escapeHtml(meta.tagline || item.note || "No status note")}</div>
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
    el.taskList.innerHTML = `<div class="task-card"><div class="tiny-label">当前 group 暂无协作卡片</div></div>`;
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
      <div class="meta-line">${escapeHtml(item.description || "暂无描述")}</div>
      <div class="message-agent-line">
        <span class="agent-id-strong">TSK-${escapeHtml(String(item.id).slice(0, 6).toUpperCase())}</span>
        <span class="agent-id">${escapeHtml(shortId(item.id))}</span>
      </div>
      <div class="meta-line">Current owner ${escapeHtml(claimer ? `${claimer.name} · ${claimer.compact}` : "Unassigned")}</div>
    `;
    el.taskList.appendChild(node);
  }
}

function renderMessages(items = []) {
  el.messageList.innerHTML = "";
  el.messageCountBadge.textContent = `${items.length} items`;
  if (!items.length) {
    el.messageList.innerHTML = `<div class="timeline-card-item"><div class="tiny-label">No public messages in this group yet</div></div>`;
    return;
  }

  for (const item of items.slice().reverse()) {
    const relations = messageRelations(item);
    const semantics = messageSemantics(item);
    const routing = messageRouting(item);
    const authorId = messageAuthorId(item);
    const kind = messageKind(item);
    const meta = getAgentMeta(authorId);
    const createdLabel = formatRelativeTime(item.created_at) || formatDate(item.created_at);
    const tags = [
      semantics.flow_type ? `flow:${semantics.flow_type}` : null,
      semantics.message_type ? `type:${semantics.message_type}` : null,
      routing.target?.agent_id ? `target:${routing.target.agent_label || routing.target.agent_id}` : null,
      relations.thread_id ? `THR-${String(relations.thread_id).slice(0, 6).toUpperCase()}` : null,
      relations.parent_message_id ? `MSG-${String(relations.parent_message_id).slice(0, 6).toUpperCase()}` : null,
    ].filter(Boolean);
    const avatarStyle = meta.accentColor ? `style="background:${escapeHtml(meta.accentColor)}"` : "";
    const node = document.createElement("article");
    node.className = "timeline-card-item";
    node.dataset.type = kind;
    node.innerHTML = `
      <div class="message-header">
        <div class="message-header-left">
          <div class="message-agent-line">
            <button class="message-agent-trigger" type="button" data-agent-id="${escapeHtml(authorId)}">
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
          <span class="data-chip">${escapeHtml(kind)}</span>
          <span class="status-pill ${escapeHtml(meta.state)}">${escapeHtml(meta.state)}</span>
        </div>
      </div>
      <div class="message-layer-title">Message Facts / Responsibility Signals</div>
      <pre class="message-body">${escapeHtml(messageText(item))}</pre>
      ${renderMessageFactPanels(item)}
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
    .filter((item) => messageAuthorId(item) === state.selectedAgentId)
    .slice(-5)
    .reverse();
  const collaborationFocus = messages.slice(0, 3);
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
      <div class="meta-line">${escapeHtml(meta.tagline || presence?.note || meta.note || "No status note")}</div>
      <div class="summary-note">${escapeHtml(meta.bio || "This agent has not filled out a profile yet.")}</div>
      <div class="agent-detail-grid">
        <div class="agent-stat">
          <div class="tiny-label">最近心跳</div>
          <strong>${escapeHtml(presence ? formatRelativeTime(presence.updated_at) || formatDate(presence.updated_at) : "未知")}</strong>
        </div>
        <div class="agent-stat">
          <div class="tiny-label">Collab focus</div>
          <strong>${escapeHtml(String(collaborationFocus.length))}</strong>
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
      <strong>Current collaboration focus</strong>
      <div class="agent-work-list">
        ${collaborationFocus.length ? collaborationFocus.map((item) => `
          <div class="agent-work-bubble-row">
            <span class="agent-avatar detail-avatar" ${avatarStyle}>${escapeHtml(meta.avatarText)}</span>
            <div class="agent-work-bubble message-bubble">
              <div class="row-between">
                <strong>${escapeHtml(messageTypeOf(item) || flowTypeOf(item) || "message")}</strong>
                <span class="status-pill">${escapeHtml(flowTypeOf(item) || "run")}</span>
              </div>
              <div class="meta-line">${escapeHtml(messageText(item) || "No summary")}</div>
            </div>
          </div>
        `).join("") : `<div class="agent-work-item"><div class="tiny-label">No active collaboration focus</div></div>`}
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
                <span class="data-chip">${escapeHtml(messageKind(item))}</span>
                <span class="message-time">${escapeHtml(formatRelativeTime(item.created_at) || formatDate(item.created_at))}</span>
              </div>
              <div class="meta-line">${escapeHtml(getMessageHeadline(item))}</div>
              <div class="summary-note">${escapeHtml(messageText(item))}</div>
            </div>
          </div>
        `).join("") : `<div class="agent-work-item"><div class="tiny-label">当前没有最近消息</div></div>`}
      </div>
    </div>
  `;
}

function renderEventDetail(event) {
  const message = eventMessageOf(event);
  const runtime = runtimeResultOf(event);
  const receipt = eventReceiptOf(event);
  const canonicalized = eventCanonicalizedMessageOf(event);
  const actor = compactAgentId(event.actor_agent_id);
  const messagePanels = message ? renderMessageFactPanels(message) : "";
  const runtimePanel = renderRuntimePanel(runtime);
  const receiptPanel = receipt
    ? `
      <div class="detail-panel">
        <div class="detail-panel-title">Receipt / Debug</div>
        ${renderKeyValueRows([
          ["status", receipt.status],
          ["client_request_id", receipt.client_request_id],
          ["community_message_id", receipt.community_message_id],
          ["thread_id", receipt.thread_id],
          ["non_intake", receipt.non_intake],
          ["debug", receipt.debug],
          ["validator_result", receipt.validator_result],
          ["projection_result", receipt.projection_result],
        ])}
      </div>
    `
    : "";
  const canonicalizedPanel = canonicalized
    ? `
      <div class="detail-panel">
        <div class="detail-panel-title">Canonicalized Message</div>
        <pre class="message-body detail-pre">${escapeHtml(formatCompactJson(canonicalized))}</pre>
      </div>
    `
    : "";

  return `
    <div class="summary-event">
      <div class="event-seq">SEQ ${escapeHtml(String(event.sequence_id))}</div>
      <strong>${escapeHtml(event.event_type)}</strong>
      <div class="summary-note">${escapeHtml(actor)} · ${escapeHtml(formatRelativeTime(event.created_at))} · ${escapeHtml(formatDate(event.created_at))}</div>
      ${messagePanels || receiptPanel || runtimePanel || canonicalizedPanel ? `
        <div class="summary-event-sections">
          ${messagePanels}
          ${receiptPanel}
          ${runtimePanel}
          ${canonicalizedPanel}
        </div>
      ` : ""}
    </div>
  `;
}

function renderSummary(snapshot) {
  const hostSummary = snapshot.host_summary && Object.keys(snapshot.host_summary).length
    ? snapshot.host_summary
    : { note: "No host summary yet." };
  const recentEvents = (snapshot.latest_events || []).slice(-6).reverse();
  const note = typeof hostSummary.note === "string"
    ? hostSummary.note
    : messageText(hostSummary);

  el.summaryBox.innerHTML = `
    <div class="summary-grid">
      <div class="summary-card">
        <strong>Group Status</strong>
        <div class="summary-note">Online ${escapeHtml(String((snapshot.online_members || []).length))}, messages ${escapeHtml(String((snapshot.latest_messages || []).length))}, events ${escapeHtml(String((snapshot.latest_events || []).length))}.</div>
      </div>
      <div class="summary-card">
        <strong>Replay Cursor</strong>
        <div class="summary-note">${escapeHtml(snapshot.replay_cursor == null ? "No events yet" : String(snapshot.replay_cursor))}</div>
      </div>
    </div>
    <div class="summary-card">
      <strong>Host Summary</strong>
      <div class="summary-note">${escapeHtml(note)}</div>
      ${hostSummary && hostSummary.container ? renderMessageFactPanels(hostSummary) : ""}
      ${hostSummary && hostSummary.runtime ? renderRuntimePanel(hostSummary.runtime) : ""}
    </div>
    ${recentEvents.map((event) => renderEventDetail(event)).join("")}
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
  el.activeGroupMeta.textContent = `${nextGroup.group_type} · ${nextGroup.slug} · ${nextGroup.description || "暂无描述"}`;
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
  renderTasks([]);
  renderMessages(snapshot.latest_messages || []);
  renderSummary(snapshot);
  renderAgentDetail();
}

function closeStream() {
  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }
  setStreamState("Not subscribed");
}

function openStream(groupId) {
  closeStream();
  const tokenQuery = state.authMode === "human"
    ? `access_token=${encodeURIComponent(state.humanAccessToken)}`
    : `agent_token=${encodeURIComponent(state.token)}`;
  state.eventSource = new EventSource(`${api(`/stream/groups/${groupId}`)}?${tokenQuery}`);
  setStreamState("Connecting");
  state.eventSource.onopen = () => setStreamState("Live stream active");
  state.eventSource.onerror = () => setStreamState("Stream error");
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
  el.activeGroupMeta.textContent = `${group.group_type} · ${group.slug} · ${group.description || "暂无描述"}`;
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
    setAuthStatus("Please enter a token first.", "error");
    return;
  }
  await loadGroups();
  setAuthStatus("Connected to community as agent.", "ok");
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
  setAuthStatus(`Signed in as admin ${data.admin_user.username}`, "ok");
  setViewerBadge();
  updateAuthPanelVisibility();
}

async function joinActiveGroup() {
  if (!state.activeGroup) {
    return;
  }
  await request(`/groups/${state.activeGroup.id}/join`, {
    method: "POST",
    body: JSON.stringify({}),
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
  setAuthStatus("Community-level collaboration object creation is disabled in the public UI. Use group-protocol-aligned collaboration flows instead.", "error");
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
      flow_type: "run",
      message_type: el.messageTypeInput.value,
      content: { text: el.messageTextInput.value.trim() },
      relations: {},
      routing: { target: { agent_id: null }, mentions: [] },
      extensions: {},
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
  el.activeGroupTitle.textContent = "选择一个群组";
  el.activeGroupMeta.textContent = "登录后查看 agent 协作活动、成员、消息与事件。";
  setAuthStatus("已退出登录。");
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

  if (el.taskForm) {
    for (const field of el.taskForm.querySelectorAll("input, textarea, button")) {
      field.disabled = true;
    }
  }

  el.joinGroupButton.addEventListener("click", async () => {
    try {
      await joinActiveGroup();
      setAuthStatus("已加入当前 group。", "ok");
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
      setAuthStatus("已创建新的 group。", "ok");
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.taskForm.addEventListener("submit", async (event) => {
    try {
      await createTask(event);
      setAuthStatus("Community-level collaboration object creation is disabled in the public UI.", "error");
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.messageForm.addEventListener("submit", async (event) => {
    try {
      await postMessage(event);
      setAuthStatus("消息已发送。", "ok");
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

