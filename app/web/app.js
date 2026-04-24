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
  groupMessages: [],
  groupSession: null,
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
  const payload = messagePayload(content);
  return payloadSummary(payload);
}

const WORKFLOW_STAGE_LABELS = {
  step1: "步骤 1 / 启动对齐",
  step2: "步骤 2 / 能力确认",
  step3: "步骤 3 / 就绪确认",
  task_start: "正式开工",
  task_plan: "任务规划",
  material_collect: "素材收集",
  draft_compile: "成稿整理",
  final_deliver: "最终交付",
};

const ROLE_LABELS = {
  manager: "经理",
  worker: "执行者",
  material_collect: "素材收集",
  draft_compile: "成稿整理",
  server: "服务端",
  system: "系统",
};

const PAYLOAD_KIND_LABELS = {
  bootstrap_task_brief: "开机任务简报",
  startup_plan: "启动计划",
  capability_summary: "能力确认总结",
  readiness_summary: "就绪确认总结",
  startup_handoff_package: "开工交接包",
  task_plan: "任务规划",
  candidate_material_pool: "候选素材池",
  approved_material_pool: "素材审批结果",
  draft_report_v1: "新闻成稿",
  draft_acceptance: "成稿验收",
  final_report: "最终报告",
};

function messagePayload(content) {
  if (!content) {
    return {};
  }
  if (content.content && typeof content.content === "object") {
    return messagePayload(content.content);
  }
  const payload = content.payload;
  return payload && typeof payload === "object" ? payload : {};
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function firstNonEmptyObject(values = []) {
  for (const value of values) {
    const candidate = objectValue(value);
    if (Object.keys(candidate).length) {
      return candidate;
    }
  }
  return null;
}

function messageStatusBlock(message) {
  return objectValue(message?.status_block);
}

function messageFormalWorkflowId(message) {
  return String(messageStatusBlock(message).workflow_id || "").trim();
}

function messageFormalStageId(message) {
  return String(messageStatusBlock(message).step_id || "").trim();
}

function messageFormalStepStatus(message) {
  return String(messageStatusBlock(message).step_status || "").trim();
}

function messageFormalRole(message) {
  return String(messageStatusBlock(message).author_role || "").trim();
}

function snapshotEmbeddedGroupSession(snapshot) {
  const communityV2 = objectValue(objectValue(snapshot?.group?.metadata_json).community_v2);
  return objectValue(communityV2.group_session);
}

function groupSessionFromEvent(event) {
  const payload = objectValue(event?.payload);
  return firstNonEmptyObject([payload.group_session, payload.group_session_declaration]);
}

function latestProjectedGroupSession(snapshot) {
  const events = Array.isArray(snapshot?.latest_events) ? snapshot.latest_events : [];
  for (let index = events.length - 1; index >= 0; index -= 1) {
    if (String(events[index]?.event_type || "") !== "group_session.updated") {
      continue;
    }
    const sessionView = groupSessionFromEvent(events[index]);
    if (sessionView) {
      return sessionView;
    }
  }
  return null;
}

function authoritativeGroupSession(snapshot = state.snapshot, directSession = state.groupSession) {
  return firstNonEmptyObject([
    directSession,
    snapshotEmbeddedGroupSession(snapshot),
    latestProjectedGroupSession(snapshot),
  ]);
}

function gateSnapshotOf(groupSession) {
  return objectValue(groupSession?.gate_snapshot);
}

function authoritativeStageLabel(groupSession) {
  const stageId = String(groupSession?.current_stage || "").trim();
  return stageId ? readableStageLabel(stageId) : "未提供";
}

function authoritativeGroupMeta(group, groupSession) {
  const sessionView = objectValue(groupSession);
  if (group && String(sessionView.group_id || "") === String(group.id || "")) {
    return [
      sessionView.workflow_id,
      sessionView.current_mode,
      authoritativeStageLabel(sessionView),
    ].filter(Boolean).join(" / ");
  }
  return group?.slug || group?.group_type || "group_session";
}

function readableStageLabel(value) {
  const key = String(value || "").trim();
  return WORKFLOW_STAGE_LABELS[key] || key;
}

function readableRoleLabel(value) {
  const key = String(value || "").trim();
  return ROLE_LABELS[key] || key;
}

function readablePayloadKindLabel(value) {
  const key = String(value || "").trim();
  return PAYLOAD_KIND_LABELS[key] || key;
}

function workflowStageIdOf(message) {
  return messageFormalStageId(message);
}

function relatedMessageIdOf(message) {
  const payload = messagePayload(message);
  return payload.related_message_id || payload.final_report_ref || payload.task_brief_ref || "";
}

function valueText(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => valueText(item)).filter(Boolean).join("、");
  }
  if (typeof value === "object") {
    return value.topic_title || value.headline || value.name || value.title || value.ref || value.id || "";
  }
  return String(value);
}

function payloadSummary(payload) {
  const kind = String(payload?.kind || "").trim();
  if (!kind) {
    return "";
  }
  const itemCount = Array.isArray(payload?.items)
    ? payload.items.length
    : Array.isArray(payload?.candidate_items)
      ? payload.candidate_items.length
      : Array.isArray(payload?.selected_materials)
        ? payload.selected_materials.length
        : Number(payload?.delivered_item_count || 0);

  if (kind === "candidate_material_pool") {
    return `候选素材池，${itemCount} 条候选素材`;
  }
  if (kind === "approved_material_pool") {
    return `素材审批结果，入选 ${itemCount} 条`;
  }
  if (kind === "draft_report_v1") {
    return `新闻成稿，${itemCount} 条热点`;
  }
  if (kind === "final_report") {
    return `最终报告，${itemCount} 条热点`;
  }
  if (kind === "task_plan") {
    return valueText(payload.task_breakdown || payload.handoff_summary || payload.startup_goal);
  }
  if (kind === "startup_plan" || kind === "capability_summary" || kind === "readiness_summary" || kind === "startup_handoff_package" || kind === "draft_acceptance" || kind === "bootstrap_task_brief") {
    return valueText(
      payload.final_summary
      || payload.handoff_summary
      || payload.startup_goal
      || payload.formal_workflow_summary
      || payload.blocking_summary
      || payload.issue_summary
      || payload.task_goal
    );
  }
  return readablePayloadKindLabel(kind);
}

function renderArtifactRows(entries = []) {
  const rows = entries
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([label, value]) => `
      <div class="workflow-kv">
        <div class="workflow-kv-label">${escapeHtml(label)}</div>
        <div class="workflow-kv-value">${escapeHtml(valueText(value))}</div>
      </div>
    `);
  return rows.length ? `<div class="workflow-artifact-grid">${rows.join("")}</div>` : "";
}

function renderSimpleList(items = [], emptyText = "暂无内容") {
  if (!Array.isArray(items) || !items.length) {
    return `<div class="workflow-list-empty">${escapeHtml(emptyText)}</div>`;
  }
  return `
    <div class="workflow-list">
      ${items.map((item) => `
        <div class="workflow-list-item">${escapeHtml(valueText(item) || "-")}</div>
      `).join("")}
    </div>
  `;
}

function imageReferenceOf(item = {}) {
  return item.image_url || item.image_attachment_ref || item.image_ref || item.image_candidate || "";
}

function renderImageReference(item = {}) {
  const ref = imageReferenceOf(item);
  if (!ref) {
    return `<div class="workflow-image-missing">未提供图片引用</div>`;
  }
  const safeRef = escapeHtml(ref);
  if (/^https?:\/\//i.test(ref)) {
    return `
      <div class="workflow-image-wrap">
        <img class="workflow-image" src="${safeRef}" alt="${escapeHtml(item.headline || item.topic_title || "image")}" loading="lazy" referrerpolicy="no-referrer" />
        <a class="workflow-image-link" href="${safeRef}" target="_blank" rel="noreferrer">查看原图</a>
      </div>
    `;
  }
  return `<div class="workflow-image-ref">图片引用：${safeRef}</div>`;
}

function renderMaterialCards(items = []) {
  if (!Array.isArray(items) || !items.length) {
    return `<div class="workflow-list-empty">暂无候选素材</div>`;
  }
  return `
    <div class="news-card-list">
      ${items.map((item, index) => `
        <article class="news-card">
          <div class="news-card-head">
            <span class="news-rank">#${escapeHtml(String(index + 1))}</span>
            <h4>${escapeHtml(item.topic_title || item.headline || "未命名素材")}</h4>
          </div>
          <div class="news-card-copy">${escapeHtml(item.core_fact_summary || item.why_hot || "")}</div>
          ${renderArtifactRows([
            ["来源", item.source],
            ["发布时间", item.published_at],
            ["为什么热", item.why_hot],
            ["可信度说明", item.credibility_note],
          ])}
          ${renderImageReference(item)}
        </article>
      `).join("")}
    </div>
  `;
}

function renderMaterialPoolSection(title, items = [], emptyText) {
  const canUseCards = Array.isArray(items) && items.some((item) => item && typeof item === "object" && (item.topic_title || item.headline || item.core_fact_summary || item.image_candidate || item.image_url));
  return `
    <div class="workflow-section">
      <h5>${escapeHtml(title)}</h5>
      ${canUseCards ? renderMaterialCards(items) : renderSimpleList(items, emptyText)}
    </div>
  `;
}

function renderNewsItems(items = []) {
  if (!Array.isArray(items) || !items.length) {
    return `<div class="workflow-list-empty">暂无新闻条目</div>`;
  }
  return `
    <div class="news-card-list">
      ${items.map((item) => `
        <article class="news-card">
          <div class="news-card-head">
            <span class="news-rank">#${escapeHtml(String(item.rank || "-"))}</span>
            <h4>${escapeHtml(item.headline || "未命名条目")}</h4>
          </div>
          <div class="news-card-copy">${escapeHtml(item.brief_100_words || "")}</div>
          ${renderArtifactRows([
            ["来源", item.source_ref],
            ["入选原因", item.why_selected],
          ])}
          ${renderImageReference(item)}
        </article>
      `).join("")}
    </div>
  `;
}

function renderRawPayloadDetails(payload) {
  return `
    <details class="workflow-raw">
      <summary>查看原始数据</summary>
      <pre>${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
    </details>
  `;
}

function renderStructuredPayload(message) {
  const payload = messagePayload(message);
  const kind = String(payload.kind || "").trim();
  if (!kind || !PAYLOAD_KIND_LABELS[kind]) {
    return "";
  }

  const stageLabel = readableStageLabel(workflowStageIdOf(message));
  const roleLabel = readableRoleLabel(messageFormalRole(message));
  const stepStatus = messageFormalStepStatus(message);
  const title = readablePayloadKindLabel(kind);
  const summary = payloadSummary(payload);
  let body = "";

  if (kind === "candidate_material_pool") {
    body = renderMaterialCards(payload.candidate_items || []);
  } else if (kind === "approved_material_pool") {
    body = `
      ${renderMaterialPoolSection("入选素材", payload.selected_materials || [], "暂无入选素材")}
      ${renderMaterialPoolSection("剔除素材", payload.rejected_materials || [], "暂无剔除素材")}
      ${renderArtifactRows([
        ["剔除原因", payload.rejection_reasons],
        ["证据引用", payload.evidence_refs],
      ])}
    `;
  } else if (kind === "draft_report_v1" || kind === "final_report") {
    body = `
      ${renderArtifactRows([
        ["报告标题", payload.report_title],
        ["最终摘要", payload.final_summary],
        ["交付数量", payload.delivered_item_count],
        ["正文可直接渲染", payload.renderable_body_present],
      ])}
      ${payload.report_markdown ? `<div class="workflow-markdown">${escapeHtml(payload.report_markdown)}</div>` : ""}
      ${renderNewsItems(payload.items || [])}
    `;
  } else {
    body = renderArtifactRows([
      ["启动目标", payload.startup_goal],
      ["任务目标", payload.task_goal],
      ["工作流说明", payload.formal_workflow_summary],
      ["角色分工", payload.role_assignments],
      ["完成定义", payload.completion_definition],
      ["开放问题", payload.open_questions],
      ["参与者状态", payload.participant_states],
      ["阻塞摘要", payload.blocking_summary],
      ["就绪参与者", payload.ready_participants],
      ["未就绪参与者", payload.not_ready_participants],
      ["交接摘要", payload.handoff_summary],
      ["第一动作", payload.first_action],
      ["任务拆解", payload.task_breakdown],
      ["验收规则", payload.acceptance_rules],
      ["交接规则", payload.handoff_rule],
      ["问题摘要", payload.issue_summary],
      ["缺失项", payload.missing_items],
      ["证据引用", payload.evidence_refs],
      ["任务简报引用", payload.task_brief_ref],
      ["最终报告引用", payload.final_report_ref],
      ["制品引用", payload.artifact_refs],
    ]);
  }

  return `
    <section class="workflow-artifact">
      <div class="workflow-artifact-head">
        <div>
          <div class="workflow-artifact-kind">${escapeHtml(title)}</div>
          <div class="workflow-artifact-stage">${escapeHtml([stageLabel, roleLabel, stepStatus].filter(Boolean).join(" / "))}</div>
        </div>
      </div>
      ${summary ? `<div class="workflow-artifact-summary">${escapeHtml(summary)}</div>` : ""}
      ${body}
      ${renderRawPayloadDetails(payload)}
    </section>
  `;
}

function renderMessageBody(message) {
  const text = messageText(message);
  const structured = renderStructuredPayload(message);
  if (structured) {
    return `
      ${text ? `<div class="timeline-bubble">${escapeHtml(text)}</div>` : ""}
      ${structured}
    `;
  }
  return `<div class="timeline-bubble">${escapeHtml(text || messageHeadline(message))}</div>`;
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
    button.textContent = panel.classList.contains("is-collapsed") ? "▸" : "▾";
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
  el.toggleRailButton.textContent = state.railCollapsed ? "▸" : "◂";
  localStorage.setItem("community.railCollapsed", state.railCollapsed ? "1" : "0");
}

function handleAuthFailure(message = "登录已过期，请重新登录。") {
  clearStoredAuth();
  state.authMode = "human";
  state.groups = [];
  state.activeGroup = null;
  state.snapshot = null;
  state.groupMessages = [];
  state.groupSession = null;
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
  el.activeGroupMeta.textContent = "group_session";
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

async function loadRecentGroupMessages(groupId, limit = 200) {
  const data = await request(
    `/messages?group_id=${encodeURIComponent(groupId)}&limit=${limit}&offset=0&newest_first=true`,
    { method: "GET" },
  );
  return Array.isArray(data?.items) ? data.items : [];
}

async function loadGroupSession(groupId) {
  return request(`/groups/${groupId}/session`, { method: "GET" });
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

function messageStageForKind(message) {
  const stepStatus = String(messageFormalStepStatus(message) || "").trim().toLowerCase();
  if (stepStatus === "closed" || stepStatus === "complete" || stepStatus === "completed" || stepStatus === "accepted") {
    return { word: stepStatus, tone: "is-result" };
  }
  if (stepStatus === "review" || stepStatus === "pending_review") {
    return { word: stepStatus, tone: "is-status" };
  }
  if (stepStatus) {
    return { word: stepStatus, tone: "is-run" };
  }
  const flowType = String(messageSemantics(message).flow_type || message?.flow_type || "").trim().toLowerCase();
  if (flowType === "start") {
    return { word: "start", tone: "is-start" };
  }
  if (flowType === "result") {
    return { word: "result", tone: "is-result" };
  }
  return { word: "run", tone: "is-run" };
}

function messageSubtypeLabel(message) {
  const payloadKind = messagePayload(message).kind;
  if (payloadKind && PAYLOAD_KIND_LABELS[payloadKind]) {
    return readablePayloadKindLabel(payloadKind);
  }
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
  const payload = messagePayload(message);
  if (payload.kind && PAYLOAD_KIND_LABELS[payload.kind]) {
    const parts = [
      readableStageLabel(workflowStageIdOf(message)),
      readablePayloadKindLabel(payload.kind),
    ].filter(Boolean);
    return parts.join(" 路 ");
  }
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

function setWorkflowMetricCard(metricNode, value, label) {
  if (!metricNode) {
    return;
  }
  metricNode.textContent = String(value ?? "-");
  const card = metricNode.closest(".metric-card");
  const labelNode = card?.querySelector(".metric-label");
  if (labelNode) {
    labelNode.textContent = label;
  }
}

function summarizeEvent(event) {
  const actor = getAgentMeta(event?.actor_agent_id);
  const message = eventMessageOf(event);
  const receipt = eventReceiptOf(event);
  const type = String(event?.event_type || "event.updated");
  const payload = messagePayload(message);
  const actorLabel = message?.author_kind === "system" || !event?.actor_agent_id ? "系统" : actor.name;
  let text = `${actorLabel}: 更新了协作状态`;

  if (type === "group_session.updated") {
    const sessionView = groupSessionFromEvent(event);
    const gateSnapshot = gateSnapshotOf(sessionView);
    const gates = objectValue(gateSnapshot.gates);
    const totalGates = Object.keys(gates).length;
    const satisfiedGateCount = Array.isArray(gateSnapshot.satisfied_gates) ? gateSnapshot.satisfied_gates.length : 0;
    const nextStageText = gateSnapshot.next_stage_allowed && gateSnapshot.next_stage
      ? ` / next ${readableStageLabel(gateSnapshot.next_stage)}`
      : "";
    text = `${actorLabel}: ${authoritativeStageLabel(sessionView)} / ${gateSnapshot.current_stage_complete ? "ready" : "waiting"} / gates ${satisfiedGateCount}/${totalGates}${nextStageText}`;
  } else if (type === "broadcast.delivered") {
    text = `${actorLabel}: ${messageHeadline(message || {})}`;
  } else if (type.includes("message")) {
    const stageLabel = readableStageLabel(workflowStageIdOf(message));
    const stepStatus = messageFormalStepStatus(message);
    const roleLabel = readableRoleLabel(messageFormalRole(message));
    const summary = payloadSummary(payload) || messageHeadline(message || {});
    text = `${actorLabel}: ${[stageLabel, stepStatus, roleLabel, summary].filter(Boolean).join(" / ")}`;
  } else if (type.includes("presence")) {
    text = `${actorLabel}: 状态变更为 ${actor.stateLabel}`;
  } else if (type.includes("status")) {
    text = `${actorLabel}: 工作流状态已更新`;
  } else if (receipt?.status) {
    text = `${actorLabel}: 回执状态 ${receipt.status}`;
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
        <span class="presence-subtitle">${escapeHtml(subtitle)}</span>
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
  const sessionView = authoritativeGroupSession();
  const gateSnapshot = gateSnapshotOf(sessionView);
  const gates = objectValue(gateSnapshot.gates);
  const gateEntries = Object.entries(gates);
  const satisfiedGateCount = Array.isArray(gateSnapshot.satisfied_gates) ? gateSnapshot.satisfied_gates.length : 0;
  const workflowLabel = String(sessionView?.workflow_id || "").trim() || "group_session";
  const currentStageValue = sessionView ? authoritativeStageLabel(sessionView) : "未提供";
  const currentStageStatus = !sessionView
    ? "未同步"
    : gateSnapshot.current_stage_complete
      ? "已满足"
      : "待满足";
  const nextStageValue = gateSnapshot.next_stage_allowed && gateSnapshot.next_stage
    ? readableStageLabel(gateSnapshot.next_stage)
    : "未开放";
  const gateProgressValue = gateEntries.length ? `${satisfiedGateCount}/${gateEntries.length}` : "0/0";

  el.taskCount.textContent = String(messages.length);
  el.timelineHint.textContent = sessionView
    ? [workflowLabel, sessionView.current_mode].filter(Boolean).join(" / ")
    : state.activeGroup
      ? "等待 group session"
      : "等待选择群组";

  setWorkflowMetricCard(el.workflowPendingCount, currentStageValue, "当前阶段");
  setWorkflowMetricCard(el.workflowActiveCount, currentStageStatus, "阶段状态");
  setWorkflowMetricCard(el.workflowReviewCount, gateProgressValue, "门控进度");
  setWorkflowMetricCard(el.workflowDoneCount, nextStageValue, "下一阶段");

  el.taskList.innerHTML = gateEntries.length
    ? gateEntries.map(([gateId, gate]) => {
      const gateInfo = objectValue(gate);
      const gateStatus = gateInfo.satisfied ? "已满足" : "待满足";
      const matchedCount = typeof gateInfo.matched_count === "number" ? gateInfo.matched_count : 0;
      return `<div class="task-card">${escapeHtml(gateId)} · ${escapeHtml(gateStatus)} · ${escapeHtml(String(matchedCount))}</div>`;
    }).join("")
    : sessionView
      ? `<div class="task-card">当前没有 authoritative gate snapshot</div>`
      : `<div class="task-card">等待 authoritative group session</div>`;
}

function renderMessages(items = []) {
  const orderedMessages = items.slice().sort((left, right) => new Date(right.created_at || 0) - new Date(left.created_at || 0));
  el.messageCountBadge.textContent = String(orderedMessages.length);

  if (!orderedMessages.length) {
    el.messageList.innerHTML = `<div class="timeline-empty">当前群组还没有公开消息</div>`;
    return;
  }

  el.messageList.innerHTML = orderedMessages.map((message, index) => {
    const authorId = messageAuthorId(message);
    const meta = getAgentMeta(authorId);
    const relations = messageRelations(message);
    const stage = messageStageForKind(message);
    const subtype = messageSubtypeLabel(message);
    const routeLabel = messageRouteLabel(message, orderedMessages);
    const replyAlias = `m${index + 1}`;
    const routing = messageRouting(message);
    const previousAuthorId = index < orderedMessages.length - 1 ? messageAuthorId(orderedMessages[index + 1]) : null;
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
              ${buildAgentAvatar(meta, "agent-avatar-large")}
            </button>
          </div>
          <div class="timeline-entry-main">
            <div class="timeline-meta-row">
              <button class="message-agent-trigger" type="button" data-agent-id="${escapeHtml(authorId || "")}">
                <span class="timeline-agent-name">${escapeHtml(meta.name)}</span>
              </button>
              <span class="timeline-agent-role">${escapeHtml(readableRoleLabel(messageFormalRole(message)) || meta.identity || meta.rawName)}</span>
              <span class="timeline-time">${escapeHtml(formatTimeOnly(message.created_at))}</span>
              <span class="timeline-stage-word ${escapeHtml(stage.tone)}">${escapeHtml(stage.word)}</span>
              <span class="timeline-stage-type">${escapeHtml(subtype)}</span>
            </div>
            <div class="timeline-card-shell">
              ${renderMessageBody(message)}
            </div>
            <div class="timeline-link-row">
              <span class="timeline-route">→ ${escapeHtml(routeLabel)}</span>
              <span class="timeline-reply-link">回复 ${escapeHtml(replyAlias)}</span>
              ${workflowStageIdOf(message) ? `<span class="timeline-extra">阶段 ${escapeHtml(readableStageLabel(workflowStageIdOf(message)))}</span>` : ""}
              ${messageFormalStepStatus(message) ? `<span class="timeline-extra">status ${escapeHtml(messageFormalStepStatus(message))}</span>` : ""}
              ${relatedMessageIdOf(message) ? `<span class="timeline-extra">引用 ${escapeHtml(shortId(relatedMessageIdOf(message)))}</span>` : ""}
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
  const messages = (state.groupMessages || [])
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
      <div class="agent-detail-id">${escapeHtml(meta.handleText || meta.compact)} 路 ${escapeHtml(meta.short)}</div>
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

  const sessionView = authoritativeGroupSession(snapshot);
  const events = (snapshot.latest_events || [])
    .slice()
    .sort((left, right) => new Date(left.created_at || 0) - new Date(right.created_at || 0))
    .slice(-6);

  const hostSummaryText = typeof snapshot.host_summary?.note === "string"
    ? snapshot.host_summary.note
    : "";

  if (!events.length && !hostSummaryText && !sessionView) {
    el.summaryBox.innerHTML = `<div class="summary-empty">褰撳墠娌℃湁鍙睍绀虹殑浜嬩欢娴?/div>`;
    return;
  }

  const blocks = [];

  if (sessionView) {
    const gateSnapshot = gateSnapshotOf(sessionView);
    const gates = objectValue(gateSnapshot.gates);
    const totalGates = Object.keys(gates).length;
    const satisfiedGateCount = Array.isArray(gateSnapshot.satisfied_gates) ? gateSnapshot.satisfied_gates.length : 0;
    blocks.push(`
      <div class="summary-event">
        <div class="summary-event-head">
          <span class="summary-event-type">group.session</span>
          ${gateSnapshot.last_evaluated_at ? `<span class="summary-event-time">${escapeHtml(formatTimeOnly(gateSnapshot.last_evaluated_at))}</span>` : ""}
        </div>
        <div class="summary-event-text">${escapeHtml([
          sessionView.workflow_id,
          sessionView.current_mode,
          authoritativeStageLabel(sessionView),
          `gates ${satisfiedGateCount}/${totalGates}`,
        ].filter(Boolean).join(" / "))}</div>
      </div>
    `);
  }

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
    state.snapshot = null;
    state.groupMessages = [];
    state.groupSession = null;
    state.membersById = new Map();
    state.presenceById = new Map();
    localStorage.removeItem("community.activeGroupId");
    el.activeGroupTitle.textContent = "请选择一个群组";
    el.activeGroupMeta.textContent = "group_session";
    renderPresence([]);
    renderTasks([]);
    renderMessages([]);
    renderSummary(null);
    renderAgentDetail();
    renderMembersPopover();
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
  el.activeGroupMeta.textContent = authoritativeGroupMeta(nextGroup, state.groupSession);
  renderGroups();
}

async function loadSnapshot(groupId) {
  const [snapshot, allMessages, groupSession] = await Promise.all([
    request(`/projection/groups/${groupId}/snapshot`, { method: "GET" }),
    loadRecentGroupMessages(groupId),
    loadGroupSession(groupId).catch(() => null),
  ]);
  state.snapshot = snapshot;
  state.groupMessages = allMessages;
  state.groupSession = authoritativeGroupSession(snapshot, groupSession);

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

  if (state.activeGroup && String(state.activeGroup.id) === String(groupId)) {
    el.activeGroupMeta.textContent = authoritativeGroupMeta(state.activeGroup, state.groupSession);
  }

  renderPresence(snapshot.online_members || []);
  renderTasks(state.groupMessages || []);
  renderMessages(state.groupMessages || []);
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
  el.activeGroupMeta.textContent = authoritativeGroupMeta(group, null);
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
    throw new Error("请先选择群组。");
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
  setAuthStatus("当前公开 UI 还没有开放社区级协作对象创建。", "error");
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
  state.groupMessages = [];
  state.groupSession = null;
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
  el.activeGroupMeta.textContent = "group_session";
  renderGroups();
  renderPresence([]);
  renderTasks([]);
  renderMessages([]);
  renderSummary(null);
  renderAgentDetail();
  renderMembersPopover();
  setMembersPopover(false);
  setAccountPopover(false);
  setAuthStatus("已退出登录。", "info");
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
    setAuthStatus("已保留新建群组入口，但当前高保真壳层还没有直接开放创建流程。", "info");
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
