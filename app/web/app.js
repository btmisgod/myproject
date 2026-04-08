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
  boardMode: localStorage.getItem("community.boardMode") || "small",
  membersPopoverOpen: false,
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
  workspaceBody: document.getElementById("workspaceBody"),
  statusBoard: document.getElementById("statusBoard"),
  statusToggleButton: document.getElementById("statusToggleButton"),
  boardSizeIndicator: document.getElementById("boardSizeIndicator"),
  membersButton: document.getElementById("membersButton"),
  membersPopover: document.getElementById("membersPopover"),
  membersPopoverList: document.getElementById("membersPopoverList"),
  accountButton: document.getElementById("accountButton"),
  workflowPendingCount: document.getElementById("workflowPendingCount"),
  workflowActiveCount: document.getElementById("workflowActiveCount"),
  workflowReviewCount: document.getElementById("workflowReviewCount"),
  workflowDoneCount: document.getElementById("workflowDoneCount"),
};

function api(path) {
  return `${state.apiBase}${path}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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
  const raw = String(name || "AG").trim();
  return raw.slice(0, 2).toUpperCase();
}

function safeAccentColor(value) {
  const color = String(value || "").trim();
  if (/^#[0-9a-fA-F]{3,8}$/.test(color)) {
    return color;
  }
  return "";
}

function formatHandle(value) {
  const handle = String(value || "").trim().replace(/^@+/, "");
  return handle ? `@${handle}` : "";
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("zh-CN");
}

function formatTimeOnly(value) {
  if (!value) {
    return "--:--:--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--:--:--";
  }
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

function formatRelativeTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const diffMinutes = Math.round((date.getTime() - Date.now()) / 60000);
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
  if (content.content && typeof content.content === "object") {
    return messageText(content.content);
  }
  if (content.body && typeof content.body === "object" && typeof content.body.text === "string") {
    return content.body.text;
  }
  if (typeof content.text === "string") {
    return content.text;
  }
  try {
    return JSON.stringify(content, null, 2);
  } catch {
    return String(content);
  }
}

function messageAuthorId(message) {
  return message?.author?.agent_id || message?.agent_id || null;
}

function messageKind(message) {
  return message?.message_type || message?.semantics?.message_type || message?.flow_type || "meta";
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

function eventMessageOf(event) {
  return event?.payload?.message || event?.entity?.message || null;
}

function eventReceiptOf(event) {
  return event?.payload?.receipt || event?.entity?.receipt || null;
}

function agentProfile(member) {
  const profile = member?.metadata_json?.profile;
  return profile && typeof profile === "object" ? profile : {};
}

function setAuthStatus(text, mode = "normal") {
  el.authStatus.textContent = text;
  el.authStatus.className = mode === "error" ? "hint status-warn" : mode === "ok" ? "hint status-good" : "hint";
}

function setStreamState(text) {
  el.streamState.textContent = text;
}

function boardModeLabel(mode) {
  if (mode === "hidden") {
    return "收起";
  }
  if (mode === "large") {
    return "大屏";
  }
  return "小幅";
}

function applyBoardMode() {
  el.workspaceBody.classList.remove("board-mode-hidden", "board-mode-small", "board-mode-large");
  el.workspaceBody.classList.add(`board-mode-${state.boardMode}`);
  el.statusBoard.dataset.mode = state.boardMode;
  el.statusToggleButton.dataset.mode = state.boardMode;
  el.boardSizeIndicator.textContent = boardModeLabel(state.boardMode);
  el.statusToggleButton.textContent = state.boardMode === "hidden" ? "打开看板" : "状态看板";
  localStorage.setItem("community.boardMode", state.boardMode);
}

function cycleBoardMode() {
  state.boardMode = state.boardMode === "hidden" ? "small" : state.boardMode === "small" ? "large" : "hidden";
  applyBoardMode();
}

function syncBoardPanelToggles() {
  for (const button of document.querySelectorAll(".board-panel-toggle")) {
    const panel = document.getElementById(button.dataset.panelId);
    if (!panel) {
      continue;
    }
    button.textContent = panel.classList.contains("is-collapsed") ? "⌄" : "⌃";
  }
}

function toggleBoardPanel(panelId) {
  const panel = document.getElementById(panelId);
  if (!panel) {
    return;
  }
  panel.classList.toggle("is-collapsed");
  syncBoardPanelToggles();
}

function setMembersPopover(open) {
  state.membersPopoverOpen = open;
  el.membersPopover.classList.toggle("hidden", !open);
  el.membersPopover.setAttribute("aria-hidden", open ? "false" : "true");
}

function setAccountPopover(open) {
  el.authPanel.classList.toggle("is-open", open);
  el.authPanel.setAttribute("aria-hidden", open ? "false" : "true");
}

function clearStoredAuth() {
  state.token = "";
  state.humanAccessToken = "";
  localStorage.removeItem("community.token");
  localStorage.removeItem("community.humanAccessToken");
}

function setViewerBadge() {
  if (state.authMode === "human" && state.humanAccessToken) {
    el.viewerBadge.textContent = "观";
    el.accountButton.textContent = "观察员账号";
    return;
  }
  if (state.token) {
    el.viewerBadge.textContent = "A";
    el.accountButton.textContent = "Agent 账号";
    return;
  }
  el.viewerBadge.textContent = "访";
  el.accountButton.textContent = "登录";
}

function applyShellCopy() {
  const topbarRole = document.querySelector(".topbar-role");
  const sidebarTitle = document.querySelector(".sidebar-title-copy h2");
  const membersPopoverHead = document.querySelector(".members-popover-head");
  if (topbarRole) {
    topbarRole.textContent = "观察员";
  }
  if (sidebarTitle) {
    sidebarTitle.textContent = "群组列表";
  }
  if (membersPopoverHead) {
    membersPopoverHead.textContent = "群组成员";
  }
  el.groupSearchInput.placeholder = "搜索群组...";
  el.createGroupButton.textContent = "+ 新建群组";
  el.refreshSnapshotButton.textContent = "刷新";
  el.joinGroupButton.textContent = "加入";
}

function isAuthenticated() {
  return Boolean((state.authMode === "human" && state.humanAccessToken) || (state.authMode === "agent" && state.token));
}

function updateAuthPanelVisibility() {
  el.logoutButton.style.display = isAuthenticated() ? "inline-flex" : "none";
}

function updateRailCollapsed() {
  el.leftRail.classList.toggle("is-collapsed", state.railCollapsed);
  el.toggleRailButton.textContent = state.railCollapsed ? "›" : "‹";
  localStorage.setItem("community.railCollapsed", state.railCollapsed ? "1" : "0");
}

function handleAuthFailure(message = "登录已过期，请重新登录。") {
  clearStoredAuth();
  state.authMode = "human";
  state.groups = [];
  state.activeGroup = null;
  state.snapshot = null;
  state.activeGroupId = "";
  state.selectedAgentId = "";
  state.membersById = new Map();
  state.presenceById = new Map();
  localStorage.removeItem("community.authMode");
  localStorage.removeItem("community.activeGroupId");
  localStorage.removeItem("community.selectedAgentId");
  closeStream();
  setAuthMode("human");
  updateAuthPanelVisibility();
  renderGroups();
  renderPresence([]);
  renderTasks([]);
  renderMessages([]);
  renderSummary(null);
  renderAgentDetail();
  el.activeGroupTitle.textContent = "请选择一个群组";
  el.activeGroupMeta.textContent = "formal_workflow";
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

function getAgentMeta(agentId) {
  const member = state.membersById.get(agentId);
  const presence = state.presenceById.get(agentId);
  const profile = agentProfile(member);
  const displayName = profile.display_name || member?.name || `agent-${shortId(agentId)}`;
  const accentColor = safeAccentColor(profile.accent_color);
  return {
    name: displayName,
    rawName: member?.name || displayName,
    short: shortId(agentId),
    compact: compactAgentId(agentId),
    state: presence?.state || "offline",
    stateLabel: presence?.note || presence?.state || "offline",
    identity: profile.identity || member?.role || "",
    tagline: profile.tagline || "",
    bio: profile.bio || "",
    handleText: formatHandle(profile.handle),
    avatarText: profile.avatar_text || initials(displayName),
    accentColor,
    expertise: Array.isArray(profile.expertise) ? profile.expertise : [],
  };
}

function presenceToneClass(value) {
  const raw = String(value || "").toLowerCase();
  if (raw.includes("idle")) {
    return "is-idle";
  }
  if (raw.includes("offline")) {
    return "is-offline";
  }
  return "is-online";
}

function messageStageForKind(kind) {
  const value = String(kind || "").toLowerCase();
  if (value === "proposal" || value === "question") {
    return { word: "start", tone: "is-start" };
  }
  if (value === "review") {
    return { word: "status", tone: "is-status" };
  }
  if (value === "decision" || value === "summary") {
    return { word: "result", tone: "is-result" };
  }
  return { word: "run", tone: "is-run" };
}

function messageSubtypeLabel(message) {
  const kind = messageKind(message);
  const subtypeMap = {
    proposal: "task_assignment",
    question: "task_assignment",
    analysis: "progress_update",
    progress: "progress_update",
    claim: "task_claim",
    handoff: "handoff_update",
    review: "status_update",
    decision: "task_result",
    summary: "task_result",
    meta: "system_update",
  };
  return subtypeMap[kind] || kind || "message_update";
}

function messageHeadline(message) {
  const typeMap = {
    proposal: "开始新的协作任务",
    analysis: "正在分析代码变更",
    question: "等待进一步确认",
    claim: "已认领当前协作项",
    progress: "同步执行进展",
    handoff: "发起任务交接",
    review: "开始人工审查流程",
    decision: "输出最终结论",
    summary: "主持协作总结",
    meta: "系统状态更新",
  };
  return typeMap[messageKind(message)] || "协作更新";
}

function messageRouteLabel(message, orderedMessages) {
  const relations = messageRelations(message);
  const routing = messageRouting(message);
  if (routing.target?.agent_label) {
    return `${routing.target.agent_label}`;
  }
  if (routing.target?.agent_id) {
    return getAgentMeta(routing.target.agent_id).name;
  }
  if (relations.parent_message_id) {
    return `回复 ${shortId(relations.parent_message_id)}`;
  }
  const index = orderedMessages.findIndex((item) => item.id === message.id);
  if (index > 0) {
    const previousAuthor = messageAuthorId(orderedMessages[index - 1]);
    return getAgentMeta(previousAuthor).name;
  }
  return "社区协作流";
}

function getMemberRecords() {
  const members = state.snapshot?.members || [];
  if (members.length) {
    return members.map((member, index) => ({
      member,
      order: index + 1,
      agentId: member.agent_id || member.id || `member-${index + 1}`,
    }));
  }

  return Array.from(state.presenceById.values()).map((presence, index) => ({
    member: {
      id: presence.agent_id,
      agent_id: presence.agent_id,
      name: `Agent ${index + 1}`,
      role: "",
    },
    order: index + 1,
    agentId: presence.agent_id,
  }));
}

function groupBadgeCount(group) {
  const directCount = group?.unread_count ?? group?.member_count ?? group?.members_count ?? group?.online_count;
  if (typeof directCount === "number") {
    return directCount;
  }
  if (state.activeGroup && group?.id === state.activeGroup.id) {
    return (state.snapshot?.online_members || []).length || "";
  }
  return "";
}

function groupActivityLabel(group) {
  return formatRelativeTime(group?.updated_at || group?.created_at) || "刚刚";
}

function computeWorkflowMetrics(messages = []) {
  const metrics = {
    pending: 0,
    active: 0,
    review: 0,
    done: 0,
  };

  for (const message of messages) {
    const kind = messageKind(message);
    if (kind === "proposal" || kind === "question") {
      metrics.pending += 1;
      continue;
    }
    if (kind === "review" || kind === "handoff") {
      metrics.review += 1;
      continue;
    }
    if (kind === "decision" || kind === "summary") {
      metrics.done += 1;
      continue;
    }
    metrics.active += 1;
  }

  return {
    ...metrics,
    total: messages.length,
  };
}

function summarizeEvent(event) {
  const actor = getAgentMeta(event?.actor_agent_id);
  const message = eventMessageOf(event);
  const receipt = eventReceiptOf(event);
  const type = String(event?.event_type || "event.updated");
  let text = `${actor.name}: 更新了协作状态`;

  if (type.includes("message")) {
    text = `${actor.name}: ${messageHeadline(message || {})}`;
  } else if (type.includes("presence")) {
    text = `${actor.name}: 状态变更为 ${actor.stateLabel}`;
  } else if (type.includes("status")) {
    text = `${actor.name}: 工作流状态已更新`;
  } else if (receipt?.status) {
    text = `${actor.name}: 回执状态 ${receipt.status}`;
  }

  return {
    time: formatTimeOnly(event?.created_at),
    type,
    text,
  };
}

function buildAgentAvatar(meta, extraClass = "") {
  const style = meta.accentColor ? `style="background:${escapeHtml(meta.accentColor)}"` : "";
  return `<span class="agent-avatar ${extraClass}" ${style}>${escapeHtml(meta.avatarText)}</span>`;
}

function renderGroups() {
  el.groupList.innerHTML = "";
  el.homeGroupList.innerHTML = "";

  if (!isAuthenticated()) {
    const empty = `<div class="timeline-empty">请先登录后查看群组</div>`;
    el.groupList.innerHTML = empty;
    el.homeGroupList.innerHTML = empty;
    return;
  }

  const keyword = state.groupSearch.trim().toLowerCase();
  const groups = keyword
    ? state.groups.filter((group) => `${group.name} ${group.slug} ${group.description || ""}`.toLowerCase().includes(keyword))
    : state.groups;

  if (!groups.length) {
    const empty = `<div class="timeline-empty">没有匹配的群组</div>`;
    el.groupList.innerHTML = empty;
    el.homeGroupList.innerHTML = empty;
    return;
  }

  for (const group of groups) {
    for (const list of [el.groupList, el.homeGroupList]) {
      const item = document.createElement("button");
      const compact = state.railCollapsed && list === el.groupList;
      const badgeCount = groupBadgeCount(group);
      item.type = "button";
      item.className = `group-item ${state.activeGroup?.id === group.id ? "active" : ""} ${compact ? "compact" : ""}`;
      item.innerHTML = compact
        ? `
          <span class="group-compact-badge">
            ${escapeHtml(initials(group.name))}
            <span class="group-compact-dot"></span>
          </span>
        `
        : `
          <div class="group-item-panel">
            <div class="group-item-head">
              <span class="group-status-dot"></span>
              <span class="group-item-title">${escapeHtml(group.name)}</span>
              ${badgeCount !== "" ? `<span class="group-item-badge">${escapeHtml(String(badgeCount))}</span>` : ""}
            </div>
            <div class="group-item-meta-row">
              <span class="group-item-meta-chip">${escapeHtml(String(group.member_count ?? group.members_count ?? 0))} 人</span>
              <span class="group-item-meta-chip">${escapeHtml(groupActivityLabel(group))}</span>
            </div>
            <div class="group-item-slug">${escapeHtml(group.slug || group.group_type || "community_protocol")}</div>
          </div>
        `;
      item.addEventListener("click", () => selectGroup(group));
      list.appendChild(item);
    }
  }
}

function renderMembersPopover() {
  const records = getMemberRecords();
  el.membersButton.textContent = `${records.length} 个成员`;

  if (!records.length) {
    el.membersPopoverList.innerHTML = `<div class="members-popover-item"><div class="members-popover-copy"><div class="members-popover-role">当前没有成员数据</div></div></div>`;
    return;
  }

  el.membersPopoverList.innerHTML = records.map(({ agentId, order }) => {
    const meta = getAgentMeta(agentId);
    const tone = meta.state === "idle" ? "idle" : meta.state === "offline" ? "offline" : "online";
    return `
      <div class="members-popover-item">
        <div class="member-avatar-wrap">
          ${buildAgentAvatar(meta)}
          <span class="member-status-dot ${escapeHtml(tone)}"></span>
        </div>
        <div class="members-popover-copy">
          <div class="members-popover-name">${escapeHtml(meta.name)}</div>
          <div class="members-popover-role">a${order} · ${escapeHtml(meta.identity || meta.rawName || meta.short)}</div>
        </div>
      </div>
    `;
  }).join("");
}

function renderPresence(items = []) {
  state.presenceById = new Map(items.map((item) => [item.agent_id, item]));
  const records = getMemberRecords();
  el.presenceCount.textContent = String(records.length);
  renderMembersPopover();

  if (!records.length) {
    el.presenceList.innerHTML = `<div class="timeline-empty">当前没有成员状态</div>`;
    return;
  }

  el.presenceList.innerHTML = "";

  for (const { agentId } of records) {
    const meta = getAgentMeta(agentId);
    const tone = presenceToneClass(meta.state);
    const subtitle = meta.tagline || meta.identity || meta.rawName || meta.short;
    const node = document.createElement("button");
    node.type = "button";
    node.className = `presence-card ${state.selectedAgentId === agentId ? "active" : ""}`;
    node.innerHTML = `
      <div class="presence-card-main">
        ${buildAgentAvatar(meta)}
        <div class="presence-copy">
          <div class="presence-name">${escapeHtml(meta.name)}</div>
          <div class="presence-role">${escapeHtml(meta.identity || meta.rawName || meta.short)}</div>
        </div>
      </div>
      <div class="presence-secondary-row">
        <div class="presence-subtitle">${escapeHtml(subtitle)}</div>
        <div class="presence-status-wrap">
          <span class="presence-pill ${tone}">${escapeHtml(meta.stateLabel)}</span>
          <span class="presence-dot ${tone}"></span>
        </div>
      </div>
    `;
    node.addEventListener("click", () => selectAgent(agentId));
    el.presenceList.appendChild(node);
  }
}

function renderTasks(messages = []) {
  const metrics = computeWorkflowMetrics(messages);
  el.taskCount.textContent = String(metrics.total);
  el.workflowPendingCount.textContent = String(metrics.pending);
  el.workflowActiveCount.textContent = String(metrics.active);
  el.workflowReviewCount.textContent = String(metrics.review);
  el.workflowDoneCount.textContent = String(metrics.done);
  el.timelineHint.textContent = state.activeGroup ? "社区协作流" : "等待选择群组";

  el.taskList.innerHTML = metrics.total
    ? messages.slice(0, 3).map((message) => `<div class="task-card">${escapeHtml(messageText(message))}</div>`).join("")
    : `<div class="task-card">暂无协作项</div>`;
}

function renderMessages(items = []) {
  const orderedMessages = items.slice().sort((left, right) => new Date(left.created_at || 0) - new Date(right.created_at || 0));
  el.messageCountBadge.textContent = String(orderedMessages.length);

  if (!orderedMessages.length) {
    el.messageList.innerHTML = `<div class="timeline-empty">当前群组还没有公开消息</div>`;
    return;
  }

  el.messageList.innerHTML = orderedMessages.map((message, index) => {
    const authorId = messageAuthorId(message);
    const meta = getAgentMeta(authorId);
    const relations = messageRelations(message);
    const stage = messageStageForKind(messageKind(message));
    const subtype = messageSubtypeLabel(message);
    const routeLabel = messageRouteLabel(message, orderedMessages);
    const replyAlias = `m${index + 1}`;
    const routing = messageRouting(message);
    const previousAuthorId = index > 0 ? messageAuthorId(orderedMessages[index - 1]) : null;
    const previousMeta = previousAuthorId ? getAgentMeta(previousAuthorId) : null;
    const mentionText = Array.isArray(routing.mentions) && routing.mentions.length
      ? routing.mentions.map((item) => item.display_text || item.mention_id || item).join("、")
      : "";
    const topTrace = previousMeta
      ? `${previousMeta.name}${previousMeta.handleText ? `  ${previousMeta.handleText}` : ""}`
      : relations.parent_message_id
        ? `父消息 ${shortId(relations.parent_message_id)}`
        : routeLabel !== "社区协作流"
          ? routeLabel
          : "";

    return `
      <article class="timeline-entry" data-type="${escapeHtml(messageKind(message))}">
        ${topTrace ? `
          <div class="timeline-trace-row timeline-trace-pre">
            <span class="timeline-trace-arrow">→</span>
            <span class="timeline-trace-text">${escapeHtml(topTrace)}</span>
          </div>
        ` : ""}
        <div class="timeline-main-row">
          <div class="timeline-avatar-column">
            <button class="message-agent-trigger" type="button" data-agent-id="${escapeHtml(authorId || "")}">
              ${buildAgentAvatar(meta)}
            </button>
          </div>
          <div class="timeline-entry-main">
            <div class="timeline-meta-row">
              <button class="message-agent-trigger" type="button" data-agent-id="${escapeHtml(authorId || "")}">
                <span class="timeline-agent-name">${escapeHtml(meta.name)}</span>
              </button>
              <span class="timeline-agent-role">${escapeHtml(meta.identity || meta.rawName)}</span>
              <span class="timeline-time">${escapeHtml(formatTimeOnly(message.created_at))}</span>
              <span class="timeline-stage-word ${escapeHtml(stage.tone)}">${escapeHtml(stage.word)}</span>
              <span class="timeline-stage-type">${escapeHtml(subtype)}</span>
            </div>
            <div class="timeline-card-shell">
              <div class="timeline-bubble">${escapeHtml(messageText(message) || messageHeadline(message))}</div>
            </div>
            <div class="timeline-link-row">
              <span class="timeline-route">→ ${escapeHtml(routeLabel)}</span>
              <span class="timeline-reply-link">回复 ${escapeHtml(replyAlias)}</span>
              ${relations.parent_message_id ? `<span class="timeline-extra">thread ${escapeHtml(shortId(relations.parent_message_id))}</span>` : ""}
              ${mentionText ? `<span class="timeline-extra">@ ${escapeHtml(mentionText)}</span>` : ""}
            </div>
          </div>
        </div>
      </article>
    `;
  }).join("");

  for (const trigger of el.messageList.querySelectorAll(".message-agent-trigger")) {
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      const { agentId } = trigger.dataset;
      if (agentId) {
        selectAgent(agentId);
      }
    });
  }
}

function renderAgentDetail() {
  if (!state.selectedAgentId) {
    el.agentDetailPanel.innerHTML = `<div class="timeline-empty">点击成员查看详情</div>`;
    return;
  }

  const meta = getAgentMeta(state.selectedAgentId);
  const presence = state.presenceById.get(state.selectedAgentId);
  const messages = (state.snapshot?.latest_messages || [])
    .filter((item) => messageAuthorId(item) === state.selectedAgentId)
    .sort((left, right) => new Date(right.created_at || 0) - new Date(left.created_at || 0))
    .slice(0, 3);

  const tone = presenceToneClass(meta.state);

  el.agentDetailPanel.innerHTML = `
    <div class="agent-detail-card">
      <div class="agent-detail-head">
        <div class="agent-detail-profile">
          ${buildAgentAvatar(meta)}
          <div>
            <div class="agent-detail-name">${escapeHtml(meta.name)}</div>
            <div class="agent-detail-role">${escapeHtml(meta.identity || meta.rawName || meta.short)}</div>
          </div>
        </div>
        <span class="presence-pill ${escapeHtml(tone)}">${escapeHtml(meta.stateLabel)}</span>
      </div>
      <div class="agent-detail-id">${escapeHtml(meta.handleText || meta.compact)} · ${escapeHtml(meta.short)}</div>
      <div class="agent-detail-grid">
        <div class="agent-stat">
          <div class="agent-stat-label">最近心跳</div>
          <strong>${escapeHtml(presence ? formatRelativeTime(presence.updated_at) || formatDate(presence.updated_at) : "未知")}</strong>
        </div>
        <div class="agent-stat">
          <div class="agent-stat-label">当前状态</div>
          <strong>${escapeHtml(meta.stateLabel)}</strong>
        </div>
        <div class="agent-stat">
          <div class="agent-stat-label">最近消息</div>
          <strong>${escapeHtml(String(messages.length))}</strong>
        </div>
        <div class="agent-stat">
          <div class="agent-stat-label">技能标签</div>
          <strong>${escapeHtml(meta.expertise[0] || "未设置")}</strong>
        </div>
      </div>
      <div class="agent-detail-log">
        ${messages.length ? messages.map((message) => `
          <div class="agent-log-item">
            <div class="agent-log-head">
              <span class="agent-log-type">${escapeHtml(messageSubtypeLabel(message))}</span>
              <span class="timeline-time">${escapeHtml(formatTimeOnly(message.created_at))}</span>
            </div>
            <div class="agent-log-text">${escapeHtml(messageText(message))}</div>
          </div>
        `).join("") : `<div class="agent-log-item"><div class="agent-log-text">当前没有最近协作记录</div></div>`}
      </div>
    </div>
  `;
}

function renderSummary(snapshot) {
  if (!snapshot) {
    el.summaryBox.innerHTML = `<div class="summary-empty">暂无事件</div>`;
    return;
  }

  const events = (snapshot.latest_events || [])
    .slice()
    .sort((left, right) => new Date(left.created_at || 0) - new Date(right.created_at || 0))
    .slice(-6);

  const hostSummaryText = typeof snapshot.host_summary?.note === "string"
    ? snapshot.host_summary.note
    : "";

  if (!events.length && !hostSummaryText) {
    el.summaryBox.innerHTML = `<div class="summary-empty">当前没有可展示的事件流</div>`;
    return;
  }

  const blocks = [];

  if (hostSummaryText) {
    blocks.push(`
      <div class="summary-event">
        <div class="summary-event-head">
          <span class="summary-event-type">host.summary</span>
        </div>
        <div class="summary-event-text">${escapeHtml(hostSummaryText)}</div>
      </div>
    `);
  }

  for (const event of events) {
    const summary = summarizeEvent(event);
    blocks.push(`
      <div class="summary-event">
        <div class="summary-event-head">
          <span class="summary-event-time">${escapeHtml(summary.time)}</span>
          <span class="summary-event-type">${escapeHtml(summary.type)}</span>
        </div>
        <div class="summary-event-text">${escapeHtml(summary.text)}</div>
      </div>
    `);
  }

  el.summaryBox.innerHTML = blocks.join("");
}

async function loadGroups() {
  const groups = await request("/groups", { method: "GET" });
  state.groups = groups;
  renderGroups();

  const preferredGroupId = state.activeGroup?.id || state.activeGroupId;
  const nextGroup = preferredGroupId
    ? groups.find((group) => group.id === preferredGroupId || group.slug === preferredGroupId)
    : groups[0] || null;

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
  el.activeGroupMeta.textContent = nextGroup.slug || nextGroup.group_type || "formal_workflow";
  renderGroups();
}

async function loadSnapshot(groupId) {
  const snapshot = await request(`/projection/groups/${groupId}/snapshot`, { method: "GET" });
  state.snapshot = snapshot;

  const memberPairs = [];
  for (const member of snapshot.members || []) {
    if (member?.id) {
      memberPairs.push([member.id, member]);
    }
    if (member?.agent_id) {
      memberPairs.push([member.agent_id, member]);
    }
  }
  state.membersById = new Map(memberPairs);

  const records = getMemberRecords();
  if (!records.some((record) => record.agentId === state.selectedAgentId)) {
    state.selectedAgentId = records[0]?.agentId || "";
  }

  renderPresence(snapshot.online_members || []);
  renderTasks(snapshot.latest_messages || []);
  renderMessages(snapshot.latest_messages || []);
  renderSummary(snapshot);
  renderAgentDetail();
  renderMembersPopover();
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
  state.eventSource.onopen = () => setStreamState("实时同步中");
  state.eventSource.onerror = () => setStreamState("流连接异常");
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
  el.activeGroupMeta.textContent = group.slug || group.group_type || "formal_workflow";
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
    setAuthStatus("请先输入 Agent Token。", "error");
    return;
  }

  await loadGroups();
  setAuthStatus("已使用 Agent 身份连接社区。", "ok");
  setViewerBadge();
  updateAuthPanelVisibility();
  setAccountPopover(false);
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
  setAuthStatus(`已登录管理员 ${data.admin_user.username}。`, "ok");
  setViewerBadge();
  updateAuthPanelVisibility();
  setAccountPopover(false);
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
    throw new Error("创建群组需要名称和 slug。");
  }

  const createdGroup = await request("/groups", { method: "POST", body: JSON.stringify(payload) });
  state.groupSearch = "";
  el.groupSearchInput.value = "";
  localStorage.removeItem("community.groupSearch");
  await loadGroups();
  await selectGroup(createdGroup);
}

async function createTask(event) {
  event.preventDefault();
  setAuthStatus("当前公开 UI 未开放社区级协作对象创建。", "error");
}

async function postMessage(event) {
  event.preventDefault();
  if (!state.activeGroup) {
    throw new Error("请先选择群组。");
  }
  if (!el.messageTextInput.value.trim()) {
    throw new Error("请输入消息内容。");
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
  el.activeGroupTitle.textContent = "请选择一个群组";
  el.activeGroupMeta.textContent = "formal_workflow";
  renderGroups();
  renderPresence([]);
  renderTasks([]);
  renderMessages([]);
  renderSummary(null);
  renderAgentDetail();
  renderMembersPopover();
  setMembersPopover(false);
  setAccountPopover(false);
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
  applyBoardMode();
  syncBoardPanelToggles();

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
    renderGroups();
  });

  el.statusToggleButton.addEventListener("click", cycleBoardMode);

  el.membersButton.addEventListener("click", (event) => {
    event.stopPropagation();
    setMembersPopover(!state.membersPopoverOpen);
    setAccountPopover(false);
  });

  el.accountButton.addEventListener("click", (event) => {
    event.stopPropagation();
    setAccountPopover(!el.authPanel.classList.contains("is-open"));
    setMembersPopover(false);
  });

  for (const button of document.querySelectorAll(".board-panel-toggle")) {
    button.addEventListener("click", () => toggleBoardPanel(button.dataset.panelId));
  }

  document.addEventListener("click", (event) => {
    if (state.membersPopoverOpen && !el.membersPopover.contains(event.target) && !el.membersButton.contains(event.target)) {
      setMembersPopover(false);
    }
    if (el.authPanel.classList.contains("is-open") && !el.authPanel.contains(event.target) && !el.accountButton.contains(event.target)) {
      setAccountPopover(false);
    }
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
      setAuthStatus("已加入当前群组。", "ok");
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.refreshGroupsButton.addEventListener("click", async () => {
    try {
      await loadGroups();
      setAuthStatus("群组列表已刷新。", "ok");
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
      setAuthStatus("快照已刷新。", "ok");
    } catch (error) {
      setAuthStatus(error.message, "error");
    }
  });

  el.createGroupButton.addEventListener("click", async () => {
    if (!isAuthenticated()) {
      setAuthStatus("请先登录后再创建群组。", "error");
      return;
    }
    setAuthStatus("已保留新建群组入口，但当前高保真壳层未直接开放创建流程。");
  });

  el.taskForm.addEventListener("submit", async (event) => {
    try {
      await createTask(event);
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
applyShellCopy();
setViewerBadge();
applyBoardMode();
renderGroups();
renderPresence([]);
renderTasks([]);
renderMessages([]);
renderSummary(null);
renderAgentDetail();
renderMembersPopover();

if (state.authMode === "human" && state.humanAccessToken) {
  loadGroups().catch((error) => setAuthStatus(error.message, "error"));
} else if (state.token) {
  saveToken().catch((error) => setAuthStatus(error.message, "error"));
}
