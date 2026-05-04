(function () {
  const STATUS_ID = "firebaseStatus";
  const ROOT = "smart-home";

  const ROOM_FB_TO_API = {
    phong_khach: "living_room",
    phong_ngu: "bedroom",
    nha_bep: "kitchen",
    san_vuon: "garden",
  };
  const ROOM_API_TO_FB = Object.fromEntries(Object.entries(ROOM_FB_TO_API).map(([fb, api]) => [api, fb]));

  const DEVICE_FB_TO_API = {
    den: "light",
    quat: "fan",
    may_lanh: "ac",
    loc_khi: "purifier",
    tv: "tv",
    tao_am: "humidifier",
    loa: "speaker",
    hut_mui: "hood",
    hut_am: "dehumidifier",
    bom: "pump",
    camera: "camera",
  };
  const DEVICE_API_TO_FB = Object.fromEntries(Object.entries(DEVICE_FB_TO_API).map(([fb, api]) => [api, fb]));

  const SENSOR_API_TO_FB = {
    temperature: "nhiet_do",
    humidity: "do_am",
    pm25: "pm25",
    lux: "anh_sang",
    motion: "chuyen_dong",
    door_open: "cua_mo",
    gas_score: "gas_score",
    soil_moisture: "do_am_dat",
    rain: "mua",
  };

  let db = null;
  let syncTimer = null;
  let lastSyncKey = "";
  let ignoreNext = false;

  function status(text, type = "waiting") {
    const el = document.getElementById(STATUS_ID);
    if (!el) return;
    el.className = `firebase-status ${type}`;
    el.textContent = text;
  }

  function nowISO() {
    return new Date().toISOString();
  }

  function compactDevice(device) {
    const out = { on: Boolean(device && device.on) };
    ["power", "target", "mode"].forEach((key) => {
      if (device && Object.prototype.hasOwnProperty.call(device, key)) out[key] = device[key];
    });
    return out;
  }

  function compactSensors(sensors) {
    const out = {};
    Object.entries(SENSOR_API_TO_FB).forEach(([apiKey, fbKey]) => {
      if (sensors && Object.prototype.hasOwnProperty.call(sensors, apiKey)) out[fbKey] = sensors[apiKey];
    });
    return out;
  }

  function compactRootFromState(state) {
    const root = {
      mode: state?.home_mode || "Home",
      updated_at: nowISO(),
      value: {},
      commands: {},
    };

    Object.entries(state?.rooms || {}).forEach(([roomId, room]) => {
      const fbRoom = ROOM_API_TO_FB[roomId];
      if (!fbRoom) return;
      root.value[fbRoom] = {
        cam_bien: compactSensors(room.sensors || {}),
        thiet_bi: {},
      };
      root.commands[fbRoom] = {};
      Object.entries(room.devices || {}).forEach(([deviceId, device]) => {
        const fbDevice = DEVICE_API_TO_FB[deviceId];
        if (!fbDevice) return;
        root.value[fbRoom].thiet_bi[fbDevice] = compactDevice(device);
        root.commands[fbRoom][fbDevice] = Boolean(device?.on);
      });
    });
    return root;
  }

  async function postJSON(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
    return data;
  }

  async function syncFromFirebase(source = "value") {
    if (!db) return;
    const snapshot = await db.ref(ROOT).once("value");
    const root = snapshot.val() || {};
    const key = JSON.stringify({ source, value: root.value || {}, commands: root.commands || {}, mode: root.mode || "" });
    if (key === lastSyncKey) return;
    lastSyncKey = key;

    const data = await postJSON("/api/firebase/sync", { root, source });
    if (typeof window.renderAll === "function") window.renderAll(data);

    // If backend Smart Notes changed any device after sensor sync, write the
    // resolved state back to Firebase so RTDB and dashboard never disagree.
    if (data && data.state && data.state.rooms) {
      const resolvedRoot = compactRootFromState(data.state);
      ignoreNext = true;
      await db.ref(ROOT).set(resolvedRoot);
      lastSyncKey = JSON.stringify({ source: "resolved", value: resolvedRoot.value || {}, commands: resolvedRoot.commands || {}, mode: resolvedRoot.mode || "" });
      setTimeout(() => { ignoreNext = false; }, 650);
    }

    status(`Firebase: realtime synced • ${new Date().toLocaleTimeString("vi-VN")}`, "ok");
  }

  function scheduleSync(source) {
    clearTimeout(syncTimer);
    syncTimer = setTimeout(() => {
      syncFromFirebase(source).catch((err) => status(`Firebase sync: ${err.message}`, "error"));
    }, 180);
  }

  async function bootstrapMissingFields() {
    try {
      const local = await fetch("/api/state").then((r) => r.json());
      const state = local.state;
      if (!state?.rooms) return;
      const rootSnap = await db.ref(ROOT).once("value");
      const root = rootSnap.val() || {};
      const updates = {};

      if (!root.mode) updates[`${ROOT}/mode`] = state.home_mode || "Home";
      if (!root.updated_at) updates[`${ROOT}/updated_at`] = nowISO();

      Object.entries(state.rooms || {}).forEach(([roomId, room]) => {
        const fbRoom = ROOM_API_TO_FB[roomId];
        if (!fbRoom) return;
        const fbRoomData = root.value?.[fbRoom] || {};
        const fbSensors = fbRoomData.cam_bien || {};
        Object.entries(compactSensors(room.sensors || {})).forEach(([fbKey, value]) => {
          if (!Object.prototype.hasOwnProperty.call(fbSensors, fbKey)) updates[`${ROOT}/value/${fbRoom}/cam_bien/${fbKey}`] = value;
        });

        Object.entries(room.devices || {}).forEach(([deviceId, device]) => {
          const fbDevice = DEVICE_API_TO_FB[deviceId];
          if (!fbDevice) return;
          const fbDeviceData = fbRoomData.thiet_bi?.[fbDevice] || {};
          const compact = compactDevice(device);
          Object.entries(compact).forEach(([key, value]) => {
            if (!Object.prototype.hasOwnProperty.call(fbDeviceData, key)) {
              updates[`${ROOT}/value/${fbRoom}/thiet_bi/${fbDevice}/${key}`] = value;
            }
          });
          if (!Object.prototype.hasOwnProperty.call(root.commands?.[fbRoom] || {}, fbDevice)) {
            updates[`${ROOT}/commands/${fbRoom}/${fbDevice}`] = Boolean(device?.on);
          }
        });
      });

      if (Object.keys(updates).length) {
        ignoreNext = true;
        await db.ref().update(updates);
        setTimeout(() => { ignoreNext = false; }, 650);
        status(`Firebase: đã bổ sung ${Object.keys(updates).length} field thiếu`, "ok");
      }
    } catch (err) {
      status(`Firebase bootstrap: ${err.message}`, "error");
    }
  }

  function fullDeviceUpdates(roomId, deviceId, devicePatch) {
    const fbRoom = ROOM_API_TO_FB[roomId];
    const fbDevice = DEVICE_API_TO_FB[deviceId];
    if (!fbRoom || !fbDevice || !devicePatch) return null;
    const updates = { [`${ROOT}/updated_at`]: nowISO() };
    if (Object.prototype.hasOwnProperty.call(devicePatch, "on")) {
      const isOn = Boolean(devicePatch.on);
      updates[`${ROOT}/commands/${fbRoom}/${fbDevice}`] = isOn;
      updates[`${ROOT}/value/${fbRoom}/thiet_bi/${fbDevice}/on`] = isOn;
    }
    ["power", "target", "mode"].forEach((key) => {
      if (Object.prototype.hasOwnProperty.call(devicePatch, key)) {
        updates[`${ROOT}/value/${fbRoom}/thiet_bi/${fbDevice}/${key}`] = devicePatch[key];
      }
    });
    return updates;
  }

  function watch() {
    db.ref(`${ROOT}/value`).on("value", () => {
      if (ignoreNext) return;
      scheduleSync("value");
    }, (err) => status(`Firebase value: ${err.message}`, "error"));

    db.ref(`${ROOT}/commands`).on("value", () => {
      if (ignoreNext) return;
      scheduleSync("commands");
    }, (err) => status(`Firebase commands: ${err.message}`, "error"));
  }

  async function flushPending() {
    if (window.__HOMEMIND_PENDING_STATE) {
      const state = window.__HOMEMIND_PENDING_STATE;
      window.__HOMEMIND_PENDING_STATE = null;
      await window.HomeMindFirebase.pushState(state);
    }
    const pendingCommands = window.__HOMEMIND_PENDING_COMMANDS || [];
    window.__HOMEMIND_PENDING_COMMANDS = [];
    for (const item of pendingCommands) await window.HomeMindFirebase.pushCommand(item.roomId, item.deviceId, item.on);
    const pendingDevices = window.__HOMEMIND_PENDING_DEVICES || [];
    window.__HOMEMIND_PENDING_DEVICES = [];
    for (const item of pendingDevices) await window.HomeMindFirebase.pushDevice(item.roomId, item.deviceId, item.devicePatch);
  }

  function init() {
    if (!window.firebase) return status("Firebase: thiếu SDK CDN", "error");
    if (!window.HOMEMIND_FIREBASE_CONFIG) return status("Firebase: thiếu config", "error");

    try {
      const app = window.firebase.apps && window.firebase.apps.length
        ? window.firebase.app()
        : window.firebase.initializeApp(window.HOMEMIND_FIREBASE_CONFIG);
      db = window.firebase.database(app);
      window.HomeMindFirebase = {
        app,
        db,
        root: ROOT,
        maps: { ROOM_API_TO_FB, ROOM_FB_TO_API, DEVICE_API_TO_FB, DEVICE_FB_TO_API },
        async pushState(state) {
          if (!state?.rooms) return false;
          const root = compactRootFromState(state);
          ignoreNext = true;
          await db.ref(ROOT).set(root);
          lastSyncKey = JSON.stringify({ source: "push", value: root.value || {}, commands: root.commands || {}, mode: root.mode || "" });
          setTimeout(() => { ignoreNext = false; }, 650);
          status(`Firebase: đã đẩy full state • ${new Date().toLocaleTimeString("vi-VN")}`, "ok");
          return true;
        },
        async pushCommand(roomId, deviceId, on) {
          const updates = fullDeviceUpdates(roomId, deviceId, { on });
          if (!updates) return false;
          ignoreNext = true;
          await db.ref().update(updates);
          setTimeout(() => { ignoreNext = false; }, 650);
          status(`Firebase: đã đẩy ON/OFF • ${new Date().toLocaleTimeString("vi-VN")}`, "ok");
          return true;
        },
        async pushDevice(roomId, deviceId, devicePatch) {
          const updates = fullDeviceUpdates(roomId, deviceId, devicePatch);
          if (!updates) return false;
          ignoreNext = true;
          await db.ref().update(updates);
          setTimeout(() => { ignoreNext = false; }, 650);
          status(`Firebase: đã đẩy slider/device • ${new Date().toLocaleTimeString("vi-VN")}`, "ok");
          return true;
        },
        async pushTelemetry(roomId, sensors) {
          const fbRoom = ROOM_API_TO_FB[roomId];
          if (!fbRoom) return false;
          const updates = { [`${ROOT}/updated_at`]: nowISO() };
          Object.entries(compactSensors(sensors || {})).forEach(([fbKey, value]) => {
            updates[`${ROOT}/value/${fbRoom}/cam_bien/${fbKey}`] = value;
          });
          ignoreNext = true;
          await db.ref().update(updates);
          setTimeout(() => { ignoreNext = false; }, 650);
          status(`Firebase: đã đẩy sensor • ${new Date().toLocaleTimeString("vi-VN")}`, "ok");
          return true;
        },
        syncNow: syncFromFirebase,
      };

      status("Firebase: đã kết nối true realtime", "ok");
      watch();
      bootstrapMissingFields().then(() => syncFromFirebase("value"));
      flushPending().catch((err) => status(`Firebase pending: ${err.message}`, "error"));
    } catch (err) {
      status(`Firebase: ${err.message}`, "error");
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
