const $ = (id) => document.getElementById(id);

const stateStore = {
  data: null,
  poll: null,
};

const THEME_KEY = "homemind-aura-theme";
const prefersLight = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;

function applyTheme(theme) {
  const nextTheme = theme === "light" ? "light" : "dark";
  document.body.setAttribute("data-theme", nextTheme);
  localStorage.setItem(THEME_KEY, nextTheme);
}

function toggleTheme() {
  const current = document.body.getAttribute("data-theme") || "dark";
  applyTheme(current === "dark" ? "light" : "dark");
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  applyTheme(saved || (prefersLight && prefersLight.matches ? "light" : "dark"));
}

function updateScrollProgress() {
  const max = document.documentElement.scrollHeight - window.innerHeight;
  const pct = max > 0 ? (window.scrollY / max) * 100 : 0;
  $("scrollProgress") && ($("scrollProgress").style.width = `${pct}%`);
}

function updateCursorAura(x, y) {
  document.documentElement.style.setProperty("--mx", `${x}px`);
  document.documentElement.style.setProperty("--my", `${y}px`);
}

function triggerSceneWipe() {
  document.body.classList.remove("scene-changing");
  void document.body.offsetWidth;
  document.body.classList.add("scene-changing");
  setTimeout(() => document.body.classList.remove("scene-changing"), 800);
}

function updateAlertVisualMode(alerts = []) {
  const count = alerts.length;
  const critical = alerts.some((a) => ["danger", "critical", "high"].includes(String(a.level || "").toLowerCase()));
  document.body.classList.toggle("alert-mode", count > 0);
  document.body.classList.toggle("alert-critical", critical);

  const chip = $("alertVisualChip");
  if (chip) chip.textContent = critical ? "Báo động cao" : count > 0 ? "Đang cảnh báo" : "Ổn định";

  const fill = $("alertReactorFill");
  if (fill) fill.style.width = count <= 0 ? "0%" : critical ? "100%" : `${Math.min(78, 30 + count * 16)}%`;
}

function initRevealMotion() {
  const cards = Array.from(document.querySelectorAll(".reveal-card"));
  if (!("IntersectionObserver" in window)) {
    cards.forEach((el) => el.classList.add("in-view"));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add("in-view");
    });
  }, { threshold: 0.16, rootMargin: "0px 0px -8% 0px" });
  cards.forEach((el) => io.observe(el));
}


const ROOM_LABEL = {
  living_room: "Phòng khách",
  bedroom: "Phòng ngủ",
  kitchen: "Nhà bếp",
  garden: "Sân vườn",
};

const SENSOR_META = {
  temperature: ["Nhiệt độ", "°C"],
  humidity: ["Độ ẩm", "%"],
  pm25: ["PM2.5", ""],
  lux: ["Ánh sáng", "%"],
  gas_score: ["Gas", ""],
  soil_moisture: ["Đất", "%"],
  motion: ["Chuyển động", ""],
  door_open: ["Cửa", ""],
  rain: ["Mưa", ""],
};

function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fmt(value, unit = "") {
  if (value === null || value === undefined || value === "") return "--";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  const n = Number(value);
  if (Number.isFinite(n)) return `${n.toFixed(Number.isInteger(n) ? 0 : 1)}${unit}`;
  return `${value}${unit}`;
}

function toast(message, type = "info") {
  const host = $("toastHost");
  if (!host) return;
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  item.textContent = message;
  host.appendChild(item);
  setTimeout(() => item.classList.add("show"), 20);
  setTimeout(() => {
    item.classList.remove("show");
    setTimeout(() => item.remove(), 250);
  }, 2600);
}

async function api(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeout || 120000);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
    return data;
  } finally {
    clearTimeout(timer);
  }
}

async function pushFirebaseState(state) {
  if (window.HomeMindFirebase?.pushState) {
    try { await window.HomeMindFirebase.pushState(state); }
    catch (err) { toast(`Firebase: ${err.message}`, "error"); }
  } else {
    window.__HOMEMIND_PENDING_STATE = state;
  }
}

async function pushFirebaseCommand(roomId, deviceId, on) {
  if (window.HomeMindFirebase?.pushCommand) {
    try { await window.HomeMindFirebase.pushCommand(roomId, deviceId, on); }
    catch (err) { toast(`Firebase: ${err.message}`, "error"); }
  } else {
    window.__HOMEMIND_PENDING_COMMANDS = window.__HOMEMIND_PENDING_COMMANDS || [];
    window.__HOMEMIND_PENDING_COMMANDS.push({ roomId, deviceId, on });
  }
}

async function pushFirebaseDevice(roomId, deviceId, devicePatch) {
  if (window.HomeMindFirebase?.pushDevice) {
    try { await window.HomeMindFirebase.pushDevice(roomId, deviceId, devicePatch); }
    catch (err) { toast(`Firebase: ${err.message}`, "error"); }
  } else {
    window.__HOMEMIND_PENDING_DEVICES = window.__HOMEMIND_PENDING_DEVICES || [];
    window.__HOMEMIND_PENDING_DEVICES.push({ roomId, deviceId, devicePatch });
  }
}

async function loadState({ silent = false } = {}) {
  try {
    const data = await api("/api/state", { timeout: 30000 });
    renderAll(data);
    if (!silent) toast("Đã tải trạng thái", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function resetHome() {
  if (!confirm("Reset dữ liệu demo nha?")) return;
  try {
    const data = await api("/api/reset", { method: "POST", timeout: 30000 });
    renderAll(data);
    await pushFirebaseState(data.state);
    toast("Đã reset và đồng bộ Firebase", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function runHomeOS(profile = null) {
  const chosenProfile = profile || $("homeosProfile")?.value || "comfort";
  try {
    const data = await api("/api/homeos/tick", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile: chosenProfile }),
      timeout: 30000,
    });
    renderAll(data);
    renderComfortImpact(data.state?.last_comfort_plan);
    await pushFirebaseState(data.state);
    toast(`Đã tối ưu theo ${chosenProfile}`, "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function toggleDevice(roomId, deviceId, nextOn) {
  try {
    const data = await api("/api/device", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room_id: roomId, device_id: deviceId, on: nextOn }),
      timeout: 30000,
    });
    renderAll(data);
    await pushFirebaseCommand(roomId, deviceId, nextOn);
    toast(nextOn ? "Đã bật thiết bị" : "Đã tắt thiết bị", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function patchDevice(roomId, deviceId, patch) {
  try {
    const data = await api("/api/device", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room_id: roomId, device_id: deviceId, patch }),
      timeout: 30000,
    });
    renderAll(data);
    const current = data.state?.rooms?.[roomId]?.devices?.[deviceId] || patch;
    await pushFirebaseDevice(roomId, deviceId, current);
    toast("Đã cập nhật thiết bị", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

function renderAll(data) {
  if (!data || !data.state) return;
  stateStore.data = data;

  const state = data.state;
  const score = data.home_score || {};
  const energy = data.energy || {};
  const alerts = data.alerts || state.alerts || [];
  const smartNotes = data.smart_notes || state.smart_notes || [];
  const energyReport = data.energy_report || {};
  const manualOverrides = state.manual_overrides || {};

  $("homeScore").textContent = score.score ?? "--";
  $("scoreLabel").textContent = score.label || "--";
  $("scoreReasons").textContent = score.reasons?.length ? score.reasons.join(" • ") : "Nhà đang ổn, chưa có cảnh báo lớn.";
  $("energyNow").textContent = `${energy.total_w ?? "--"}W`;
  $("energyDay").textContent = `${energy.estimated_kwh_day ?? "--"} kWh/ngày`;
  $("homeMode").textContent = state.home_mode || "Home";
  $("lastUpdate").textContent = state.updated_at || "--";
  $("activeDevices").textContent = energy.active_devices?.length || 0;
  $("alertCount").textContent = `${alerts.length} cảnh báo`;

  renderRooms(state.rooms || {}, score.rooms || {}, manualOverrides);
  renderComfortImpact(state.last_comfort_plan);
  renderSmartNotes(smartNotes);
  renderAlerts(alerts);
  renderEnergyReport(energyReport);
}

function severityLabel(roomScore) {
  const sev = roomScore?.severity || "good";
  const label = roomScore?.label || (sev === "danger" ? "Nguy cơ" : sev === "warning" ? "Cần chú ý" : "Ổn");
  return { sev, label };
}

function sensorValue(key, value) {
  if (key === "motion" || key === "door_open" || key === "rain") return value ? "Có" : "Không";
  const meta = SENSOR_META[key] || [key, ""];
  return fmt(value, meta[1]);
}


function isOverrideActive(manualOverrides, roomId, deviceId) {
  const item = manualOverrides?.[`${roomId}/${deviceId}`];
  if (!item?.until) return false;
  return new Date(item.until).getTime() >= Date.now();
}

function overrideBadge(manualOverrides, roomId, deviceId) {
  return isOverrideActive(manualOverrides, roomId, deviceId)
    ? `<span class="override-badge">Smart Chat ưu tiên</span>`
    : "";
}


function renderRooms(rooms, roomScores = {}, manualOverrides = {}) {
  const host = $("roomsGrid");
  if (!host) return;

  host.innerHTML = Object.entries(rooms).map(([roomId, room]) => {
    const health = severityLabel(roomScores[roomId]);
    const sensors = Object.entries(room.sensors || {})
      .filter(([key]) => ["temperature", "humidity", "pm25", "lux", "gas_score", "soil_moisture"].includes(key))
      .map(([key, value]) => {
        const [label] = SENSOR_META[key] || [key];
        return `<div class="sensor"><span>${esc(label)}</span><b>${esc(sensorValue(key, value))}</b></div>`;
      }).join("");

    const devices = Object.entries(room.devices || {}).map(([deviceId, device]) => {
      const hasPower = Object.prototype.hasOwnProperty.call(device, "power");
      const hasTarget = Object.prototype.hasOwnProperty.call(device, "target");
      const sliders = [
        hasPower ? `
          <div class="slider-wrap">
            <label><span>Công suất</span><b>${esc(device.power)}%</b></label>
            <input type="range" min="10" max="100" value="${Number(device.power || 50)}" data-room="${esc(roomId)}" data-device="${esc(deviceId)}" data-patch="power">
          </div>` : "",
        hasTarget ? `
          <div class="slider-wrap">
            <label><span>Nhiệt độ mục tiêu</span><b>${esc(device.target)}°C</b></label>
            <input type="range" min="18" max="30" value="${Number(device.target || 26)}" data-room="${esc(roomId)}" data-device="${esc(deviceId)}" data-patch="target">
          </div>` : "",
      ].join("");

      return `
        <article class="device ${device.on ? "on" : ""}">
          <div class="device-main">
            <span class="device-icon">${esc(device.icon || "🔘")}</span>
            <div>
              <b>${esc(device.name || deviceId)}</b>
              <small>${device.on ? "Đang bật" : "Đang tắt"}</small>
              ${overrideBadge(manualOverrides, roomId, deviceId)}
            </div>
            <button class="toggle-btn" data-room="${esc(roomId)}" data-device="${esc(deviceId)}" data-next="${device.on ? "false" : "true"}">${device.on ? "ON" : "OFF"}</button>
          </div>
          ${sliders}
        </article>
      `;
    }).join("");

    return `
      <article class="room-card card">
        <header class="room-head">
          <div>
            <p class="eyebrow">${esc(room.type || "room")}</p>
            <h4>${esc(room.icon || "🏠")} ${esc(room.name || ROOM_LABEL[roomId] || roomId)}</h4>
          </div>
          <span class="room-status ${esc(health.sev)}">${esc(health.label)}</span>
        </header>
        <div class="sensor-row">${sensors}</div>
        <div class="device-list">${devices}</div>
      </article>
    `;
  }).join("");

  host.querySelectorAll(".toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => toggleDevice(btn.dataset.room, btn.dataset.device, btn.dataset.next === "true"));
  });
  host.querySelectorAll("input[type='range'][data-patch]").forEach((slider) => {
    slider.addEventListener("change", () => {
      patchDevice(slider.dataset.room, slider.dataset.device, { [slider.dataset.patch]: Number(slider.value) });
    });
  });
}

function renderComfortImpact(plan) {
  const host = $("comfortImpact");
  if (!host) return;
  if (!plan || !Array.isArray(plan.items)) {
    host.innerHTML = "Chọn một Auto Mode để hệ thống tự điều chỉnh toàn nhà theo cảm biến hiện tại.";
    return;
  }
  host.innerHTML = `
    <h4>${esc(plan.summary || "HomeOS đã tối ưu")}</h4>
    <ul>${plan.items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
  `;
}

function renderRules(rules) {
  const host = $("rulesList");
  if (!host) return;
  if (!rules || !rules.length) {
    host.innerHTML = `<div class="rule-item"><div><b>Chưa có rule</b><small>Tạo rule đầu tiên bằng form phía trên.</small></div></div>`;
    return;
  }

  host.innerHTML = rules.map((r) => {
    const action = r.action || {};
    const patch = action.patch && Object.keys(action.patch).length ? ` ${JSON.stringify(action.patch)}` : "";
    return `
      <article class="rule-item">
        <div>
          <b>${esc(r.name)}</b>
          <small>IF ${esc(r.room_id)}.${esc(r.metric)} ${esc(r.operator)} ${esc(r.value)} → ${esc(action.device_id || action.scene || "action")} ${action.on === false ? "OFF" : "ON"}${esc(patch)}</small>
        </div>
        <button class="mini-btn" data-rule-toggle="${esc(r.id)}" data-enabled="${r.enabled ? "false" : "true"}">${r.enabled ? "ON" : "OFF"}</button>
        <button class="mini-btn danger" data-rule-delete="${esc(r.id)}">Xóa</button>
      </article>
    `;
  }).join("");

  host.querySelectorAll("[data-rule-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => toggleUserRule(btn.dataset.ruleToggle, btn.dataset.enabled === "true"));
  });
  host.querySelectorAll("[data-rule-delete]").forEach((btn) => {
    btn.addEventListener("click", () => deleteUserRule(btn.dataset.ruleDelete));
  });
}

function renderAlerts(alerts) {
  const host = $("alertList");
  if (!host) return;
  if (!alerts || !alerts.length) {
    host.innerHTML = `<article class="alert-card"><b>Nhà đang ổn</b><small>Chưa có cảnh báo lớn.</small></article>`;
    updateAlertVisualMode([]);
    return;
  }
  host.innerHTML = alerts.map((a) => `
    <article class="alert-card ${esc(a.level || "info")}">
      <b>${esc(a.title || "Cảnh báo")}</b>
      <small>${esc(a.detail || "")}</small>
    </article>
  `).join("");
  updateAlertVisualMode(alerts);
}

function renderEnergyReport(report) {
  const summary = $("energyProSummary");
  const tips = $("energyTips");
  if (!summary || !tips) return;
  summary.innerHTML = `
    <article><span>Tổng tải</span><b>${esc(report.total_w ?? "--")}W</b></article>
    <article><span>kWh/ngày</span><b>${esc(report.estimated_kwh_day ?? "--")}</b></article>
    <article><span>Chi phí/ngày</span><b>${Number(report.estimated_cost_day_vnd || 0).toLocaleString("vi-VN")}đ</b></article>
  `;
  tips.innerHTML = (report.tips || []).map((tip) => `<article class="tip-card">${esc(tip)}</article>`).join("")
    || `<article class="tip-card">Điện năng hiện ổn.</article>`;
}

async function saveUserRule() {
  let patch = {};
  const rawPatch = ($("rulePatch")?.value || "").trim();
  if (rawPatch) {
    try { patch = JSON.parse(rawPatch); }
    catch { return toast("Patch JSON chưa đúng. Ví dụ: {\"power\":45}", "error"); }
  }
  const room = $("ruleRoom").value;
  const payload = {
    name: $("ruleName").value.trim() || "Rule mới",
    enabled: true,
    room_id: room,
    metric: $("ruleMetric").value,
    operator: $("ruleOperator").value,
    value: Number($("ruleValue").value),
    action: {
      type: "device",
      room_id: room,
      device_id: $("ruleDevice").value,
      on: $("ruleOn").value === "true",
      patch,
    },
  };
  try {
    const data = await api("/api/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      timeout: 30000,
    });
    renderAll(data);
    await pushFirebaseState(data.state);
    $("ruleName").value = "";
    $("rulePatch").value = "";
    toast("Đã lưu rule", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function toggleUserRule(id, enabled) {
  try {
    const data = await api("/api/rules/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, enabled }),
      timeout: 30000,
    });
    renderAll(data);
    await pushFirebaseState(data.state);
    toast("Đã cập nhật rule", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function deleteUserRule(id) {
  if (!confirm("Xóa rule này nha?")) return;
  try {
    const data = await api(`/api/rules/${encodeURIComponent(id)}`, { method: "DELETE", timeout: 30000 });
    renderAll(data);
    await pushFirebaseState(data.state);
    toast("Đã xóa rule", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}


function openChatPanel(focusInput = false) {
  document.body.classList.add("chat-open");
  $("floatingChatPanel")?.setAttribute("aria-hidden", "false");
  $("chatOverlay")?.setAttribute("aria-hidden", "false");
  if (focusInput) setTimeout(() => $("bubbleInput")?.focus(), 140);
}

function closeChatPanel() {
  document.body.classList.remove("chat-open");
  $("floatingChatPanel")?.setAttribute("aria-hidden", "true");
  $("chatOverlay")?.setAttribute("aria-hidden", "true");
}

function toggleChatPanel() {
  if (document.body.classList.contains("chat-open")) closeChatPanel();
  else openChatPanel(true);
}

function appendBubble(role, text) {
  const log = $("bubbleLog");
  if (!log) return;
  const item = document.createElement("div");
  item.className = `bubble ${role === "user" ? "user" : "ai"}`;
  item.innerHTML = esc(text || "");
  log.appendChild(item);
  log.scrollTop = log.scrollHeight;
}

async function sendSmartBubble() {
  const input = $("bubbleInput");
  const message = (input?.value || "").trim();
  if (!message) return toast("Nhập note trước nha", "error");
  appendBubble("user", message);
  input.value = "";
  appendBubble("ai", "Đang xử lý yêu cầu của bạn...");
  try {
    const data = await api("/api/smart-bubble", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      timeout: 30000,
    });
    renderAll(data);
    await pushFirebaseState(data.state);
    appendBubble("ai", data.reply || "Mình đã tạo smart note xong.");
    toast("Đã xử lý xong", "success");
  } catch (err) {
    appendBubble("ai", `Lỗi: ${err.message}`);
    toast(err.message, "error");
  }
}

function renderSmartNotes(notes) {
  const host = $("smartNotesList");
  if (!host) return;
  const noteCount = $("notesCount");
  if (noteCount) noteCount.textContent = `${(notes || []).length} note`;
  if (!notes || !notes.length) {
    host.innerHTML = `<article class="note-card"><b>Chưa có Smart Note</b><small>Mở AI Assistant để tạo note hoặc hỏi trạng thái nhà.</small></article>`;
    return;
  }
  host.innerHTML = notes.slice().reverse().map((note) => `
    <article class="note-card ${note.enabled === false ? "off" : ""}">
      <b>${esc(note.title || "Smart Note")}</b>
      <small>${esc(note.summary || "")}</small>
      <small>Phòng: ${esc(ROOM_LABEL[note.room_id] || note.room_id || "--")}</small>
      <div class="note-actions">
        <button class="mini-btn" data-note-toggle="${esc(note.id)}" data-enabled="${note.enabled === false ? "true" : "false"}">${note.enabled === false ? "Bật lại" : "Tắt note"}</button>
        <button class="mini-btn danger" data-note-delete="${esc(note.id)}">Xóa</button>
      </div>
    </article>
  `).join("");
  host.querySelectorAll("[data-note-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => toggleSmartNote(btn.dataset.noteToggle, btn.dataset.enabled === "true"));
  });
  host.querySelectorAll("[data-note-delete]").forEach((btn) => {
    btn.addEventListener("click", () => deleteSmartNote(btn.dataset.noteDelete));
  });
}

async function toggleSmartNote(id, enabled) {
  try {
    const data = await api("/api/smart-notes/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, enabled }),
      timeout: 30000,
    });
    renderAll(data);
    await pushFirebaseState(data.state);
    toast(enabled ? "Đã bật note" : "Đã tắt note", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function deleteSmartNote(id) {
  if (!confirm("Xóa Smart Note này nha?")) return;
  try {
    const data = await api(`/api/smart-notes/${encodeURIComponent(id)}`, { method: "DELETE", timeout: 30000 });
    renderAll(data);
    await pushFirebaseState(data.state);
    toast("Đã xóa note", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}


function bindScrollSpy() {
  const links = Array.from(document.querySelectorAll(".nav-link"));
  const sections = links
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  const setActive = (id) => {
    links.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${id}`));
  };

  const observer = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (visible) setActive(visible.target.id);
  }, { root: null, threshold: [0.25, 0.45, 0.65], rootMargin: "-12% 0px -60% 0px" });

  sections.forEach((section) => observer.observe(section));

  window.addEventListener("scroll", () => {
    let current = sections[0]?.id;
    for (const section of sections) {
      const rect = section.getBoundingClientRect();
      if (rect.top <= 160) current = section.id;
    }
    if (current) setActive(current);
  }, { passive: true });
}

function bindEvents() {
  $("refreshBtn")?.addEventListener("click", () => loadState());
  $("runHomeOSBtn")?.addEventListener("click", () => runHomeOS());
  $("resetBtn")?.addEventListener("click", resetHome);

  $("themeToggleBtn")?.addEventListener("click", toggleTheme);
  $("chatFab")?.addEventListener("click", toggleChatPanel);
  $("openChatBtn")?.addEventListener("click", () => openChatPanel(true));
  $("openChatBtn2")?.addEventListener("click", () => openChatPanel(true));
  $("chatCloseBtn")?.addEventListener("click", closeChatPanel);
  $("chatOverlay")?.addEventListener("click", closeChatPanel);

  $("bubbleSendBtn")?.addEventListener("click", () => { openChatPanel(); sendSmartBubble(); });
  $("bubbleInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      openChatPanel();
      sendSmartBubble();
    }
  });

  document.querySelectorAll(".quick-prompt").forEach((btn) => {
    btn.addEventListener("click", () => {
      if ($("bubbleInput")) $("bubbleInput").value = btn.dataset.prompt || "";
      openChatPanel(true);
    });
  });

  document.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", () => triggerSceneWipe());
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeChatPanel();
  });

  window.addEventListener("scroll", updateScrollProgress, { passive: true });

  document.querySelectorAll(".auto-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      triggerSceneWipe();
      if ($("homeosProfile")) $("homeosProfile").value = btn.dataset.profile || "comfort";
      runHomeOS(btn.dataset.profile || "comfort");
    });
  });

  initRevealMotion();
  bindScrollSpy();
}

window.HomeMindApp = { getData: () => stateStore.data, stateStore };
window.renderAll = renderAll;
window.loadState = loadState;
window.pushFirebaseState = pushFirebaseState;
window.pushFirebaseCommand = pushFirebaseCommand;
window.pushFirebaseDevice = pushFirebaseDevice;
window.openChatPanel = openChatPanel;
window.closeChatPanel = closeChatPanel;

initTheme();
updateScrollProgress();
bindEvents();
loadState({ silent: true });
stateStore.poll = setInterval(() => loadState({ silent: true }), 6000);
