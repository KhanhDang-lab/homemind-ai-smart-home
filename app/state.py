from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import json
import random
import re
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
STATE_FILE = DATA_DIR / "smart_home_state.json"
HISTORY_FILE = DATA_DIR / "history.json"

MAX_EVENTS = 120
MAX_HISTORY = 360

DEVICE_POWER_W = {
    "light": 12,
    "fan": 45,
    "ac": 900,
    "purifier": 55,
    "tv": 120,
    "humidifier": 35,
    "pump": 65,
    "camera": 8,
    "speaker": 18,
    "hood": 70,
    "dehumidifier": 260,
}

ROOM_ALIAS = {
    "phong khach": "living_room", "phòng khách": "living_room", "khách": "living_room", "living": "living_room",
    "phong ngu": "bedroom", "phòng ngủ": "bedroom", "ngủ": "bedroom", "bedroom": "bedroom",
    "bep": "kitchen", "bếp": "kitchen", "nha bep": "kitchen", "nhà bếp": "kitchen", "kitchen": "kitchen", "phong bep": "kitchen", "phòng bếp": "kitchen", "nha_bep": "kitchen",
    "san vuon": "garden", "sân vườn": "garden", "sân": "garden", "vườn": "garden", "garden": "garden",
}

DEVICE_ALIAS = {
    "den": "light", "đèn": "light", "light": "light",
    "quat": "fan", "quạt": "fan", "fan": "fan",
    "may lanh": "ac", "máy lạnh": "ac", "dieu hoa": "ac", "điều hòa": "ac", "ac": "ac",
    "loc khi": "purifier", "lọc khí": "purifier", "purifier": "purifier",
    "tv": "tv", "tivi": "tv",
    "tao am": "humidifier", "tạo ẩm": "humidifier", "humidifier": "humidifier",
    "bom": "pump", "bơm": "pump", "pump": "pump",
    "camera": "camera", "cam": "camera",
    "loa": "speaker", "speaker": "speaker",
    "hut mui": "hood", "hút mùi": "hood", "hut_mui": "hood", "hood": "hood", "may hut mui": "hood", "máy hút mùi": "hood",
    "hut am": "dehumidifier", "hút ẩm": "dehumidifier", "hut_am": "dehumidifier", "dehumidifier": "dehumidifier", "may hut am": "dehumidifier", "máy hút ẩm": "dehumidifier",
}

SCENES = {
    "sleep": {
        "label": "Sleep",
        "emoji": "🌙",
        "description": "AI ưu tiên phòng ngủ, tắt thiết bị dư ở phòng khác và giữ an toàn ban đêm.",
    },
    "away": {
        "label": "Away",
        "emoji": "🛡️",
        "description": "AI chuyển cả nhà sang tiết kiệm điện, giữ camera và xử lý cảnh báo môi trường.",
    },
    "focus": {
        "label": "Focus",
        "emoji": "💡",
        "description": "AI tối ưu phòng làm việc/chính, giảm nhiễu ở phòng khác và cân bằng nhiệt độ.",
    },
    "movie": {
        "label": "Movie",
        "emoji": "🎬",
        "description": "AI tối ưu phòng khách để xem phim, tắt bớt phòng không dùng và giữ bếp/sân an toàn.",
    },
    "clean_air": {
        "label": "Clean Air",
        "emoji": "🍃",
        "description": "AI bật lọc khí/hút mùi đúng phòng đang ô nhiễm, tránh bật thiết bị dư.",
    },
    "garden": {
        "label": "Garden Care",
        "emoji": "🌿",
        "description": "AI chăm sân vườn theo độ ẩm đất/ánh sáng/mưa, đồng thời tiết kiệm điện trong nhà.",
    },
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_state() -> dict[str, Any]:
    return {
        "updated_at": now_iso(),
        "home_mode": "Home",
        "last_ai": None,
        "last_scene_plan": None,
        "rooms": {
            "living_room": {
                "name": "Phòng khách",
                "type": "living",
                "icon": "🛋️",
                "color": "cyan",
                "sensors": {"temperature": 29.2, "humidity": 65, "pm25": 28, "lux": 58, "motion": True, "door_open": False},
                "devices": {
                    "light": {"name": "Đèn", "on": True, "power": 70, "icon": "💡"},
                    "fan": {"name": "Quạt", "on": False, "power": 40, "icon": "🌀"},
                    "ac": {"name": "Máy lạnh", "on": False, "target": 26, "icon": "❄️"},
                    "purifier": {"name": "Lọc khí", "on": False, "mode": "auto", "icon": "🍃"},
                    "dehumidifier": {"name": "Hút ẩm", "on": False, "mode": "auto", "icon": "💨"},
                    "tv": {"name": "TV", "on": False, "icon": "📺"},
                },
            },
            "bedroom": {
                "name": "Phòng ngủ",
                "type": "sleep",
                "icon": "🛏️",
                "color": "violet",
                "sensors": {"temperature": 28.0, "humidity": 68, "pm25": 22, "lux": 24, "motion": False, "door_open": False},
                "devices": {
                    "light": {"name": "Đèn ngủ", "on": False, "power": 25, "icon": "🌙"},
                    "fan": {"name": "Quạt", "on": True, "power": 35, "icon": "🌀"},
                    "ac": {"name": "Máy lạnh", "on": False, "target": 26, "icon": "❄️"},
                    "humidifier": {"name": "Tạo ẩm", "on": False, "icon": "💧"},
                    "dehumidifier": {"name": "Hút ẩm", "on": False, "mode": "auto", "icon": "💨"},
                    "speaker": {"name": "Loa", "on": False, "icon": "🔊"},
                },
            },
            "kitchen": {
                "name": "Nhà bếp",
                "type": "kitchen",
                "icon": "🍳",
                "color": "orange",
                "sensors": {"temperature": 30.4, "humidity": 72, "pm25": 35, "lux": 70, "motion": True, "door_open": False, "gas_score": 12},
                "devices": {
                    "light": {"name": "Đèn bếp", "on": True, "power": 80, "icon": "💡"},
                    "hood": {"name": "Hút mùi", "on": False, "power": 55, "icon": "🌫️"},
                    "dehumidifier": {"name": "Hút ẩm", "on": False, "mode": "auto", "icon": "💨"},
                    "purifier": {"name": "Lọc khí mini", "on": False, "mode": "auto", "icon": "🍃"},
                },
            },
            "garden": {
                "name": "Sân vườn",
                "type": "garden",
                "icon": "🌿",
                "color": "green",
                "sensors": {"temperature": 31.5, "humidity": 60, "pm25": 42, "lux": 86, "motion": False, "door_open": False, "soil_moisture": 38, "rain": False},
                "devices": {
                    "light": {"name": "Đèn sân", "on": False, "power": 55, "icon": "💡"},
                    "pump": {"name": "Máy bơm", "on": False, "icon": "🚿"},
                    "camera": {"name": "Camera", "on": True, "icon": "📷"},
                },
            },
        },
        "automations": [
            {"id": "auto_comfort_engine", "name": "Comfort Auto Engine", "enabled": True, "rule": "temp/humidity/pm25/lux theo ngữ cảnh", "action": "optimize whole home"},
            {"id": "auto_pm25", "name": "PM2.5 cao thì bật lọc khí", "enabled": True, "rule": "pm25 > 42", "action": "turn_on purifier"},
            {"id": "auto_night_garden", "name": "Trời tối thì bật đèn sân nhẹ", "enabled": True, "rule": "garden.lux < 18", "action": "turn_on garden light"},
            {"id": "auto_hot_room", "name": "Phòng nóng thì bật quạt", "enabled": True, "rule": "temperature > 31", "action": "turn_on fan"},
            {"id": "auto_dry_soil", "name": "Đất khô thì bật bơm sân vườn", "enabled": True, "rule": "garden.soil_moisture < 32", "action": "turn_on garden pump"},
            {"id": "auto_gas_alert", "name": "Gas cao thì bật hút mùi", "enabled": True, "rule": "kitchen.gas_score > 55", "action": "turn_on hood"},
        ],
        "user_rules": [],
        "smart_notes": [],
        "learning_profile": {},
        "manual_overrides": {},
        "alerts": [],
        "events": [],
    }


def _deep_merge_defaults(state: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Keep old saved values but add new fields introduced by v2."""
    merged = deepcopy(defaults)
    if not isinstance(state, dict):
        return merged
    for key, value in state.items():
        if key in ["rooms", "automations", "events", "last_ai", "user_rules", "smart_notes", "learning_profile", "manual_overrides", "alerts"]:
            continue
        merged[key] = value
    for room_id, room in state.get("rooms", {}).items():
        if room_id not in merged["rooms"]:
            merged["rooms"][room_id] = room
            continue
        merged_room = merged["rooms"][room_id]
        merged_room.update({k: v for k, v in room.items() if k not in ["sensors", "devices"]})
        merged_room.setdefault("sensors", {}).update(room.get("sensors", {}))
        for dev_id, dev in room.get("devices", {}).items():
            merged_room.setdefault("devices", {}).setdefault(dev_id, {}).update(dev)
    if isinstance(state.get("automations"), list) and state["automations"]:
        default_by_id = {r["id"]: r for r in defaults["automations"]}
        old_by_id = {r.get("id"): r for r in state["automations"] if r.get("id")}
        merged["automations"] = []
        for rid, rule in default_by_id.items():
            item = deepcopy(rule)
            item.update(old_by_id.get(rid, {}))
            merged["automations"].append(item)
    merged["events"] = state.get("events", [])[-MAX_EVENTS:]
    merged["user_rules"] = state.get("user_rules", defaults.get("user_rules", []))
    merged["smart_notes"] = state.get("smart_notes", defaults.get("smart_notes", []))
    merged["learning_profile"] = state.get("learning_profile", defaults.get("learning_profile", {}))
    merged["manual_overrides"] = state.get("manual_overrides", defaults.get("manual_overrides", {}))
    merged["alerts"] = state.get("alerts", defaults.get("alerts", []))[-MAX_EVENTS:]
    merged["last_ai"] = state.get("last_ai")
    return merged


def load_state() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    defaults = default_state()
    if not STATE_FILE.exists():
        save_state(defaults)
        return defaults
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        state = _deep_merge_defaults(state, defaults)
        return state
    except Exception:
        save_state(defaults)
        return defaults


def save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def add_event(state: dict[str, Any], title: str, detail: str = "", level: str = "info") -> None:
    events = state.setdefault("events", [])
    events.append({"time": now_iso(), "title": title, "detail": detail, "level": level})
    state["events"] = events[-MAX_EVENTS:]


def save_history(snapshot: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append(snapshot)
    HISTORY_FILE.write_text(json.dumps(history[-MAX_HISTORY:], ensure_ascii=False, indent=2), encoding="utf-8")


def load_history(limit: int = 90) -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))[-max(1, min(limit, MAX_HISTORY)):]
    except Exception:
        return []


def room_health(room: dict[str, Any]) -> dict[str, Any]:
    s = room.get("sensors", {})
    issues: list[str] = []
    severity = "good"

    temp = float(s.get("temperature", 0) or 0)
    humidity = float(s.get("humidity", 0) or 0)
    pm25 = float(s.get("pm25", 0) or 0)
    gas = float(s.get("gas_score", 0) or 0)
    soil = s.get("soil_moisture")

    if pm25 > 55:
        issues.append("PM2.5 cao")
        severity = "danger"
    elif pm25 > 35:
        issues.append("PM2.5 cần chú ý")
        severity = max_severity(severity, "warning")
    if temp > 32:
        issues.append("Nhiệt độ cao")
        severity = max_severity(severity, "danger")
    elif temp > 30:
        issues.append("Hơi nóng")
        severity = max_severity(severity, "warning")
    if humidity > 82:
        issues.append("Độ ẩm cao")
        severity = max_severity(severity, "warning")
    if gas > 55:
        issues.append("Gas cần kiểm tra")
        severity = max_severity(severity, "danger")
    if soil is not None and float(soil) < 32:
        issues.append("Đất hơi khô")
        severity = max_severity(severity, "warning")

    return {
        "severity": severity,
        "label": "Ổn" if severity == "good" else "Cần chú ý" if severity == "warning" else "Ưu tiên xử lý",
        "issues": issues[:5],
    }


def max_severity(a: str, b: str) -> str:
    order = {"good": 0, "warning": 1, "danger": 2}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def compute_home_score(state: dict[str, Any]) -> dict[str, Any]:
    score = 100
    reasons: list[str] = []
    room_scores: dict[str, Any] = {}
    for room_id, room in state.get("rooms", {}).items():
        s = room.get("sensors", {})
        name = room.get("name", room_id)
        penalty = 0
        pm25 = float(s.get("pm25", 0) or 0)
        temp = float(s.get("temperature", 0) or 0)
        humidity = float(s.get("humidity", 0) or 0)
        gas = float(s.get("gas_score", 0) or 0)
        soil = s.get("soil_moisture")

        if pm25 > 55:
            penalty += 16
            reasons.append(f"{name}: PM2.5 cao")
        elif pm25 > 35:
            penalty += 8
            reasons.append(f"{name}: PM2.5 cần chú ý")
        if temp > 32:
            penalty += 10
            reasons.append(f"{name}: nhiệt độ cao")
        elif temp > 30:
            penalty += 5
        if humidity > 82:
            penalty += 6
            reasons.append(f"{name}: độ ẩm cao")
        if gas > 70:
            penalty += 24
            reasons.append(f"{name}: gas_score nguy hiểm")
        elif gas > 55:
            penalty += 12
            reasons.append(f"{name}: gas_score cần kiểm tra")
        if soil is not None and float(soil) < 28:
            penalty += 5
            reasons.append(f"{name}: đất khô")
        if s.get("door_open") and state.get("home_mode") == "Away":
            penalty += 20
            reasons.append(f"{name}: cửa mở khi Away")

        score -= penalty
        room_scores[room_id] = {"score": max(0, 100 - penalty), **room_health(room)}

    score = max(0, min(100, int(score)))
    if score >= 85:
        label = "Rất ổn"
    elif score >= 70:
        label = "Ổn định"
    elif score >= 55:
        label = "Cần chú ý"
    else:
        label = "Nguy cơ cao"
    return {"score": score, "label": label, "reasons": reasons[:8], "rooms": room_scores}


def estimate_energy(state: dict[str, Any]) -> dict[str, Any]:
    total = 0.0
    room_power: dict[str, float] = {}
    active_devices: list[dict[str, Any]] = []
    for room_id, room in state.get("rooms", {}).items():
        rp = 0.0
        for device_id, device in room.get("devices", {}).items():
            if device.get("on"):
                base = DEVICE_POWER_W.get(device_id, 20)
                if "power" in device:
                    base = base * max(0.1, float(device.get("power", 100)) / 100.0)
                rp += base
                active_devices.append({"room_id": room_id, "room": room.get("name"), "device_id": device_id, "name": device.get("name"), "watts": round(base, 1)})
        room_power[room_id] = round(rp, 1)
        total += rp
    return {
        "total_w": round(total, 1),
        "room_power": room_power,
        "active_devices": active_devices,
        "estimated_kwh_day": round(total * 8 / 1000, 2),
        "estimated_cost_day_vnd": int(round(total * 8 / 1000 * 3000)),
    }


def snapshot_for_ai(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "updated_at": state.get("updated_at"),
        "home_mode": state.get("home_mode"),
        "home_score": compute_home_score(state),
        "energy": estimate_energy(state),
        "rooms": state.get("rooms", {}),
        "automations": state.get("automations", []),
        "scenes": SCENES,
        "smart_notes": state.get("smart_notes", [])[-12:],
        "learning_profile": state.get("learning_profile", {}),
        "recent_events": state.get("events", [])[-14:],
    }


def simulate_sensors() -> dict[str, Any]:
    state = load_state()
    for room_id, room in state.get("rooms", {}).items():
        s = room.get("sensors", {})
        d = room.get("devices", {})
        temp = float(s.get("temperature", 28) or 28) + random.uniform(-0.20, 0.32)
        humidity = float(s.get("humidity", 60) or 60) + random.uniform(-1.0, 1.0)
        pm25 = float(s.get("pm25", 20) or 20) + random.uniform(-1.8, 2.4)
        lux = float(s.get("lux", 50) or 50) + random.uniform(-3.0, 3.0)

        if d.get("ac", {}).get("on"):
            target = float(d["ac"].get("target", 26))
            temp += (target - temp) * 0.22
        if d.get("fan", {}).get("on"):
            temp -= 0.12
        if d.get("purifier", {}).get("on"):
            pm25 -= random.uniform(2.0, 4.8)
        if d.get("hood", {}).get("on") and "gas_score" in s:
            s["gas_score"] = max(0, float(s.get("gas_score", 10)) - random.uniform(2.0, 5.0))
        if d.get("humidifier", {}).get("on"):
            humidity += random.uniform(0.8, 1.8)

        if room_id == "garden":
            if s.get("rain"):
                humidity += 1.0
                if "soil_moisture" in s:
                    s["soil_moisture"] = min(100, float(s["soil_moisture"]) + random.uniform(1.5, 3.8))
            if d.get("pump", {}).get("on") and "soil_moisture" in s:
                s["soil_moisture"] = min(100, float(s["soil_moisture"]) + random.uniform(3.5, 6.5))

        s["temperature"] = round(max(16, min(42, temp)), 1)
        s["humidity"] = round(max(25, min(98, humidity)), 1)
        s["pm25"] = round(max(1, min(160, pm25)), 1)
        s["lux"] = round(max(0, min(100, lux)), 1)
        s["motion"] = random.random() < (0.36 if room_id != "bedroom" else 0.18)
        if random.random() < 0.035:
            s["door_open"] = not bool(s.get("door_open"))
        if "gas_score" in s:
            s["gas_score"] = round(max(0, min(100, float(s.get("gas_score", 10)) + random.uniform(-1.4, 2.2))), 1)
        if "soil_moisture" in s:
            s["soil_moisture"] = round(max(0, min(100, float(s.get("soil_moisture", 45)) - random.uniform(0.0, 0.9))), 1)

    apply_basic_automations(state)
    save_state(state)
    energy = estimate_energy(state)
    save_history({
        "time": now_iso(),
        "score": compute_home_score(state)["score"],
        "energy": energy["total_w"],
        "kwh_day": energy["estimated_kwh_day"],
    })
    return state


def rule_enabled(state: dict[str, Any], rule_id: str) -> bool:
    return any(rule.get("id") == rule_id and rule.get("enabled") for rule in state.get("automations", []))



def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or isinstance(value, bool):
            return default
        return float(value)
    except Exception:
        return default


def _device_summary(room: dict[str, Any], device_id: str, device: dict[str, Any], reason: str = "") -> str:
    status = "ON" if device.get("on") else "OFF"
    extra: list[str] = []
    if "power" in device:
        extra.append(f"{device.get('power')}%")
    if "target" in device:
        extra.append(f"{device.get('target')}°C")
    suffix = f" ({', '.join(extra)})" if extra else ""
    why = f" — {reason}" if reason else ""
    return f"{room.get('name', '')}: {device.get('name', device_id)} → {status}{suffix}{why}"



def override_key(room_id: str, device_id: str) -> str:
    return f"{room_id}/{device_id}"


def set_manual_override(state: dict[str, Any], room_id: str, device_id: str, reason: str = "manual", ttl_minutes: int = 90) -> None:
    overrides = state.setdefault("manual_overrides", {})
    overrides[override_key(room_id, device_id)] = {
        "room_id": room_id,
        "device_id": device_id,
        "reason": reason,
        "until": (datetime.now() + timedelta(minutes=max(5, ttl_minutes))).isoformat(timespec="seconds"),
        "updated_at": now_iso(),
    }


def clear_manual_overrides(state: dict[str, Any], room_id: str | None = None, device_id: str | None = None) -> None:
    overrides = state.setdefault("manual_overrides", {})
    if not room_id and not device_id:
        overrides.clear()
        return
    for key in list(overrides.keys()):
        item = overrides.get(key, {})
        if room_id and item.get("room_id") != room_id:
            continue
        if device_id and item.get("device_id") != device_id:
            continue
        overrides.pop(key, None)


def is_manual_override_active(state: dict[str, Any], room_id: str, device_id: str) -> bool:
    overrides = state.setdefault("manual_overrides", {})
    item = overrides.get(override_key(room_id, device_id))
    if not item:
        return False
    try:
        until = datetime.fromisoformat(str(item.get("until")))
        if until >= datetime.now():
            return True
    except Exception:
        pass
    overrides.pop(override_key(room_id, device_id), None)
    return False



def apply_comfort_engine(state: dict[str, Any], profile: str = "comfort", *, force: bool = False, source: str = "automation") -> list[str]:
    """Context-aware comfort controller for the whole house.

    It balances comfort + energy instead of using only one hard threshold:
    - >=32°C in occupied rooms: AC target 25-26°C + fan support.
    - 28-31.9°C: fan first, AC off to save power.
    - <25°C: cooling off; humidity devices decide based on humidity.
    - humidity high: dehumidifier if available; humidity low: humidifier if available.
    - PM2.5/gas/soil/lux are handled per room context.
    """
    profile = (profile or state.get("auto_profile") or "comfort").lower().strip()
    if profile not in {"comfort", "eco", "sleep", "movie", "away", "guest"}:
        profile = "comfort"
    state["auto_profile"] = profile

    home_mode = str(state.get("home_mode") or "Home").lower()
    if profile == "away":
        state["home_mode"] = "Away Auto"
    elif profile == "sleep":
        state["home_mode"] = "Sleep Auto"
    elif profile == "movie":
        state["home_mode"] = "Movie Auto"
    elif profile == "eco":
        state["home_mode"] = "Eco Auto"
    elif profile == "guest":
        state["home_mode"] = "Guest Auto"
    elif force:
        state["home_mode"] = "Comfort Auto"

    plan: list[str] = []

    def room(room_id: str) -> dict[str, Any]:
        return state.get("rooms", {}).get(room_id, {})

    def sensors(room_id: str) -> dict[str, Any]:
        return room(room_id).get("sensors", {})

    def device(room_id: str, device_id: str) -> dict[str, Any] | None:
        return room(room_id).get("devices", {}).get(device_id)

    def sensor(room_id: str, key: str, default: float = 0.0) -> float:
        return _to_float(sensors(room_id).get(key), default)

    def occupied(room_id: str) -> bool:
        s = sensors(room_id)
        motion = bool(s.get("motion"))
        if profile == "away" or "away" in home_mode:
            return False
        if profile == "sleep":
            return room_id == "bedroom"
        if profile == "movie":
            return room_id == "living_room" or (room_id == "kitchen" and motion)
        if profile == "guest":
            return room_id in {"living_room", "kitchen"} or motion
        return motion or room_id == "living_room"

    def turn(room_id: str, device_id: str, on: bool, patch: dict[str, Any] | None = None, reason: str = "") -> None:
        r = room(room_id)
        d = device(room_id, device_id)
        if not r or not d:
            return
        # Chat/user commands have priority. Background automation must not undo them.
        if source == "automation" and not force and is_manual_override_active(state, room_id, device_id):
            plan.append(f"{r.get('name', room_id)}: giữ nguyên {d.get('name', device_id)} vì đang có ưu tiên từ Smart Chat")
            return
        before = json.dumps({k: d.get(k) for k in ["on", "power", "target", "mode"]}, sort_keys=True, ensure_ascii=False)
        d["on"] = bool(on)
        if patch:
            for key, val in patch.items():
                if val is not None:
                    d[key] = val
        after = json.dumps({k: d.get(k) for k in ["on", "power", "target", "mode"]}, sort_keys=True, ensure_ascii=False)
        if before != after:
            plan.append(_device_summary(r, device_id, d, reason))

    def comfort_band(room_id: str) -> tuple[float, float]:
        # target min/max comfort by mode
        if profile == "sleep" and room_id == "bedroom":
            return 25.0, 28.0
        if profile == "movie" and room_id == "living_room":
            return 25.0, 28.0
        if profile == "eco":
            return 25.0, 30.5
        return 25.0, 29.5

    def hvac(room_id: str) -> None:
        r = room(room_id)
        if not r:
            return
        temp = sensor(room_id, "temperature", 28)
        hum = sensor(room_id, "humidity", 60)
        pm = sensor(room_id, "pm25", 0)
        is_occupied = occupied(room_id)
        quiet = profile in {"sleep", "movie"}
        learned = state.setdefault("learning_profile", {}).get(room_id, {}) if isinstance(state.setdefault("learning_profile", {}), dict) else {}

        # Perceived temperature: humidity and poor air make a room feel hotter.
        felt = temp + max(0, hum - 65) * 0.045 + max(0, pm - 35) * 0.018

        fan_on_at = float(learned.get("fan_on_at", 28.0))
        ac_on_at = float(learned.get("ac_on_at", 32.0))
        target_preferred = int(learned.get("ac_target", 26))

        if profile == "eco":
            fan_on_at += 0.4
            ac_on_at += 0.8
            target_preferred = max(26, target_preferred)
        elif profile == "sleep" and room_id == "bedroom":
            fan_on_at -= 0.2
            ac_on_at -= 0.6
            target_preferred = min(26, target_preferred)
        elif profile == "movie" and room_id == "living_room":
            fan_on_at -= 0.1
            ac_on_at -= 0.5
        elif profile == "guest" and room_id in {"living_room", "kitchen"}:
            fan_on_at -= 0.2
            ac_on_at -= 0.4

        if not is_occupied:
            # Empty room: save power, but still protect the house from heat/humidity.
            if felt >= 34.2 and device(room_id, "fan"):
                turn(room_id, "fan", True, {"power": 28}, f"phòng trống nhưng cảm giác nóng {felt:.1f}°C")
            else:
                if device(room_id, "fan"):
                    turn(room_id, "fan", False, reason="phòng không dùng, ưu tiên tiết kiệm điện")
                if device(room_id, "ac"):
                    turn(room_id, "ac", False, reason="phòng không dùng, chưa cần máy lạnh")
            if hum >= 78 and device(room_id, "dehumidifier"):
                turn(room_id, "dehumidifier", True, reason=f"ẩm cao {hum:g}% dù phòng không dùng")
            elif device(room_id, "dehumidifier"):
                turn(room_id, "dehumidifier", False, reason="ẩm chưa cao")
            if device(room_id, "humidifier"):
                turn(room_id, "humidifier", False, reason="phòng không dùng")
            return

        # Occupied room: comfort first, then energy optimization.
        if felt >= ac_on_at and device(room_id, "ac"):
            target = target_preferred
            if felt >= ac_on_at + 1.5:
                target = max(24, target_preferred - 1)
            if profile == "eco":
                target = max(26, target)
            fan_power = int(max(28, min(58, 30 + (felt - ac_on_at) * 8)))
            if quiet:
                fan_power = max(22, fan_power - 10)
            turn(room_id, "ac", True, {"target": target}, f"cảm giác nóng {felt:.1f}°C, máy lạnh target {target}°C")
            if device(room_id, "fan"):
                turn(room_id, "fan", True, {"power": fan_power}, "quạt hỗ trợ để máy lạnh đỡ tốn điện")
        elif felt >= fan_on_at and device(room_id, "fan"):
            fan_power = int(max(24, min(70, 30 + (felt - fan_on_at) * 11)))
            if quiet:
                fan_power = max(22, fan_power - 10)
            turn(room_id, "fan", True, {"power": fan_power}, f"cảm giác {felt:.1f}°C, dùng quạt trước để tiết kiệm điện")
            if device(room_id, "ac"):
                turn(room_id, "ac", False, reason="chưa cần máy lạnh, quạt là đủ")
        elif temp < 25:
            if device(room_id, "fan"):
                turn(room_id, "fan", False, reason=f"nhiệt độ thấp {temp:g}°C")
            if device(room_id, "ac"):
                turn(room_id, "ac", False, reason=f"nhiệt độ thấp {temp:g}°C")
        else:
            if device(room_id, "fan"):
                turn(room_id, "fan", False, reason="đang trong vùng thoải mái")
            if device(room_id, "ac"):
                turn(room_id, "ac", False, reason="đang trong vùng thoải mái")

        # Humidity strategy: avoid running humidifier/dehumidifier against each other.
        if hum >= 78 and device(room_id, "dehumidifier"):
            turn(room_id, "dehumidifier", True, reason=f"độ ẩm cao {hum:g}%")
            if device(room_id, "humidifier"):
                turn(room_id, "humidifier", False, reason="đang hút ẩm")
        elif hum <= 40 and device(room_id, "humidifier"):
            turn(room_id, "humidifier", True, reason=f"khô {hum:g}%")
            if device(room_id, "dehumidifier"):
                turn(room_id, "dehumidifier", False, reason="không cần hút ẩm")
        else:
            if device(room_id, "humidifier"):
                turn(room_id, "humidifier", False, reason="độ ẩm ổn")
            if device(room_id, "dehumidifier") and temp < 25 and hum >= 65:
                turn(room_id, "dehumidifier", True, reason=f"mát nhưng hơi ẩm {hum:g}%")
            elif device(room_id, "dehumidifier"):
                turn(room_id, "dehumidifier", False, reason="độ ẩm ổn")

    def air(room_id: str) -> None:
        pm = sensor(room_id, "pm25", 0)
        threshold_on = 32 if profile in {"clean_air", "guest"} else 38
        threshold_off = 24
        if device(room_id, "purifier"):
            if pm >= threshold_on:
                turn(room_id, "purifier", True, reason=f"PM2.5 {pm:g}")
            elif pm <= threshold_off:
                turn(room_id, "purifier", False, reason="PM2.5 ổn")

    def light(room_id: str) -> None:
        lux = sensor(room_id, "lux", 100)
        occ = occupied(room_id)
        if not device(room_id, "light"):
            return
        if occ and lux < 22:
            power = 20 if profile in {"sleep", "movie"} else 45
            turn(room_id, "light", True, {"power": power}, f"ánh sáng thấp {lux:g}%")
        elif not occ and room_id != "garden":
            turn(room_id, "light", False, reason="không có nhu cầu sử dụng")

    def kitchen() -> None:
        gas = sensor("kitchen", "gas_score", 0)
        pm = sensor("kitchen", "pm25", 0)
        temp = sensor("kitchen", "temperature", 29)
        motion = bool(sensors("kitchen").get("motion"))
        if device("kitchen", "hood"):
            if gas >= 25 or pm >= 45 or temp >= 33:
                power = 80 if gas >= 40 else 60 if pm >= 55 else 45
                turn("kitchen", "hood", True, {"power": power}, f"bếp cần thông gió gas/PM/temp {gas:g}/{pm:g}/{temp:g}")
            elif profile == "movie" and not motion:
                turn("kitchen", "hood", False, reason="movie mode, bếp không dùng")
            elif gas < 18 and pm < 35:
                turn("kitchen", "hood", False, reason="bếp ổn")

    def garden() -> None:
        s = sensors("garden")
        lux = sensor("garden", "lux", 100)
        soil = sensor("garden", "soil_moisture", 100)
        rain = bool(s.get("rain"))
        motion = bool(s.get("motion"))
        if device("garden", "camera"):
            turn("garden", "camera", True, reason="an ninh sân vườn")
        if device("garden", "light"):
            if lux < 18 and (motion or profile in {"away", "sleep"}):
                turn("garden", "light", True, {"power": 25}, "tối và cần an ninh")
            elif profile != "garden":
                turn("garden", "light", False, reason="không ra sân")
        if device("garden", "pump"):
            if soil < 30 and not rain:
                turn("garden", "pump", True, reason=f"đất khô {soil:g}%")
            elif soil >= 45 or rain:
                turn("garden", "pump", False, reason="đất đủ ẩm hoặc đang mưa")

    for rid in ["living_room", "bedroom", "kitchen"]:
        hvac(rid)
        air(rid)
        light(rid)
    kitchen()
    garden()

    if plan:
        state["last_comfort_plan"] = {
            "profile": profile,
            "items": plan[-40:],
            "summary": f"Comfort Auto đã tối ưu {len(plan)} thay đổi theo nhiệt độ, độ ẩm, PM2.5 và ngữ cảnh.",
            "updated_at": now_iso(),
        }
        if source:
            add_event(state, "Comfort Auto Engine", f"{profile}: {len(plan)} thay đổi", source)
    elif force:
        state["last_comfort_plan"] = {
            "profile": profile,
            "items": ["Nhà đang nằm trong vùng thoải mái, không cần đổi thiết bị."],
            "summary": "Comfort Auto kiểm tra xong, chưa cần thay đổi.",
            "updated_at": now_iso(),
        }
    return plan


def apply_comfort_auto(profile: str = "comfort") -> dict[str, Any]:
    state = load_state()
    apply_comfort_engine(state, profile=profile, force=True, source="auto")
    save_state(state)
    return state


def apply_basic_automations(state: dict[str, Any]) -> None:
    # Smart comfort engine is the main automation layer.
    if rule_enabled(state, "auto_comfort_engine"):
        apply_comfort_engine(state, profile=state.get("auto_profile") or "comfort", source="automation")

    apply_user_rules(state)

    for room_id, room in state.get("rooms", {}).items():
        s = room.get("sensors", {})
        d = room.get("devices", {})
        if rule_enabled(state, "auto_pm25") and s.get("pm25", 0) > 42 and "purifier" in d and not d["purifier"].get("on"):
            d["purifier"]["on"] = True
            add_event(state, f"Tự bật lọc khí ở {room['name']}", f"PM2.5 = {s.get('pm25')}", "automation")

    garden_room = state.get("rooms", {}).get("garden", {})
    gd = garden_room.get("devices", {})
    gs = garden_room.get("sensors", {})
    if rule_enabled(state, "auto_dry_soil") and gs.get("soil_moisture", 100) < 32 and "pump" in gd and not gd["pump"].get("on"):
        gd["pump"]["on"] = True
        add_event(state, "Tự bật máy bơm sân vườn", f"Độ ẩm đất = {gs.get('soil_moisture')}%", "automation")

    kitchen_room = state.get("rooms", {}).get("kitchen", {})
    kd = kitchen_room.get("devices", {})
    ks = kitchen_room.get("sensors", {})
    if rule_enabled(state, "auto_gas_alert") and ks.get("gas_score", 0) > 55 and "hood" in kd and not kd["hood"].get("on"):
        kd["hood"]["on"] = True
        kd["hood"]["power"] = 85
        add_event(state, "Tự bật hút mùi nhà bếp", f"Gas score = {ks.get('gas_score')}", "automation")

def set_device(room_id: str, device_id: str, on: bool | None = None, patch: dict[str, Any] | None = None, *, state: dict[str, Any] | None = None, save: bool = True, source: str = "manual", override_minutes: int = 90) -> dict[str, Any]:
    state = state or load_state()
    room_id = canonical_room_id(room_id)
    device_id = canonical_device_id(device_id)
    room = state.get("rooms", {}).get(room_id)
    if not room:
        raise ValueError(f"Không tìm thấy phòng: {room_id}")
    device = room.get("devices", {}).get(device_id)
    if not device:
        raise ValueError(f"Không tìm thấy thiết bị: {device_id} trong {room.get('name', room_id)}")
    if on is not None:
        device["on"] = bool(on)
    if patch:
        clean_patch = {k: v for k, v in patch.items() if k not in ["name", "icon"]}
        device.update(clean_patch)
    if source in {"manual", "chat", "firebase"}:
        set_manual_override(state, room_id, device_id, reason=source, ttl_minutes=override_minutes)
    add_event(state, f"Cập nhật {device.get('name', device_id)}", f"{room['name']} → {'ON' if device.get('on') else 'OFF'}", source if source else "device")
    if save:
        # Direct commands must not be immediately undone by background auto rules.
        save_state(state)
    return state


def update_sensors(room_id: str, sensors: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    room = state.get("rooms", {}).get(room_id)
    if not room:
        raise ValueError("room_id không hợp lệ")
    allowed = {"temperature", "humidity", "pm25", "lux", "motion", "door_open", "gas_score", "soil_moisture", "rain"}
    room["sensors"].update({k: v for k, v in sensors.items() if k in allowed})
    add_event(state, "Nhận telemetry", f"{room['name']}: {sensors}", "sensor")
    apply_basic_automations(state)
    save_state(state)
    return state


def apply_scene(scene: str, *, state: dict[str, Any] | None = None, save: bool = True) -> dict[str, Any]:
    """Apply a context-aware smart scene.

    This is intentionally deterministic and fast. Ollama can still explain/analyze,
    but pressing a scene should immediately produce useful actions based on the
    current sensors: temperature, humidity, PM2.5, lux, gas and soil moisture.
    """
    if not scene:
        raise ValueError("Scene không hợp lệ")
    state = state or load_state()
    scene = scene.lower().strip()
    if scene not in SCENES:
        raise ValueError("Scene không hợp lệ")

    plan: list[str] = []

    def room(room_id: str) -> dict[str, Any]:
        return state.get("rooms", {}).get(room_id, {})

    def sensors(room_id: str) -> dict[str, Any]:
        return room(room_id).get("sensors", {})

    def value(room_id: str, key: str, default: float = 0) -> float:
        try:
            return float(sensors(room_id).get(key, default))
        except Exception:
            return default

    def has_device(room_id: str, device_id: str) -> bool:
        return device_id in room(room_id).get("devices", {})

    def turn(room_id: str, device_id: str, on: bool = True, patch: dict[str, Any] | None = None, why: str = "") -> None:
        r = room(room_id)
        if not r:
            return
        dev = r.get("devices", {}).get(device_id)
        if not dev:
            return
        before_on = bool(dev.get("on"))
        before_extra = {k: dev.get(k) for k in ["power", "target", "mode"]}
        dev["on"] = bool(on)
        if patch:
            for key, val in patch.items():
                if val is not None:
                    dev[key] = val
        after_extra = {k: dev.get(k) for k in ["power", "target", "mode"]}
        if before_on != bool(dev.get("on")) or before_extra != after_extra:
            status = "ON" if dev.get("on") else "OFF"
            extra = []
            if "power" in dev:
                extra.append(f"{dev.get('power')}%")
            if "target" in dev:
                extra.append(f"{dev.get('target')}°C")
            suffix = f" ({', '.join(extra)})" if extra else ""
            reason = f" — {why}" if why else ""
            plan.append(f"{r.get('name', room_id)}: {dev.get('name', device_id)} → {status}{suffix}{reason}")

    def cooling_for(room_id: str, *, occupied: bool, quiet: bool = False) -> None:
        temp = value(room_id, "temperature", 28)
        if not occupied:
            # Do not cool empty rooms unless they are dangerously hot.
            if temp >= 33 and has_device(room_id, "fan"):
                turn(room_id, "fan", True, {"power": 25}, "phòng không dùng nhưng quá nóng")
            else:
                if has_device(room_id, "fan"):
                    turn(room_id, "fan", False, why="phòng không dùng")
                if has_device(room_id, "ac"):
                    turn(room_id, "ac", False, why="tiết kiệm điện")
            return

        if temp >= 31 and has_device(room_id, "ac"):
            turn(room_id, "ac", True, {"target": 25 if temp >= 33 else 26}, f"nhiệt độ {temp:g}°C")
            if has_device(room_id, "fan"):
                turn(room_id, "fan", True, {"power": 26 if quiet else 38}, "hỗ trợ lưu thông khí")
        elif temp >= 28.5:
            if has_device(room_id, "fan"):
                turn(room_id, "fan", True, {"power": 22 if quiet else 34}, f"nhiệt độ {temp:g}°C")
            if has_device(room_id, "ac"):
                turn(room_id, "ac", False, why="chỉ cần quạt để tiết kiệm điện")
        else:
            if has_device(room_id, "fan"):
                turn(room_id, "fan", False, why="nhiệt độ ổn")
            if has_device(room_id, "ac"):
                turn(room_id, "ac", False, why="nhiệt độ ổn")

    def air_quality_for(room_id: str, *, strong: bool = False) -> None:
        pm25 = value(room_id, "pm25", 0)
        if has_device(room_id, "purifier"):
            if pm25 >= (30 if strong else 42):
                turn(room_id, "purifier", True, why=f"PM2.5 {pm25:g}")
            elif strong:
                turn(room_id, "purifier", False, why="không khí ổn, tránh chạy dư")

    def kitchen_safety(*, movie_snack_mode: bool = False) -> None:
        gas = value("kitchen", "gas_score", 0)
        pm25 = value("kitchen", "pm25", 0)
        motion = bool(sensors("kitchen").get("motion"))
        lux = value("kitchen", "lux", 100)
        if has_device("kitchen", "hood"):
            if gas >= 25 or pm25 >= 45:
                turn("kitchen", "hood", True, {"power": 70 if gas >= 35 else 45}, f"gas/PM cần xử lý ({gas:g}/{pm25:g})")
            elif movie_snack_mode:
                turn("kitchen", "hood", False, why="chỉ thỉnh thoảng lấy đồ ăn, không chạy dư")
            else:
                turn("kitchen", "hood", False, why="bếp đang ổn")
        if has_device("kitchen", "light"):
            if motion and lux < 35:
                turn("kitchen", "light", True, {"power": 35}, "có người vào bếp và hơi tối")
            elif movie_snack_mode:
                turn("kitchen", "light", False, why="movie mode ưu tiên phòng khách")
            elif lux < 18:
                turn("kitchen", "light", True, {"power": 25}, "ánh sáng bếp thấp")
            else:
                turn("kitchen", "light", False, why="tiết kiệm điện")

    def garden_safety(*, active_garden: bool = False, night_guard: bool = True) -> None:
        lux = value("garden", "lux", 100)
        soil = value("garden", "soil_moisture", 100)
        rain = bool(sensors("garden").get("rain"))
        motion = bool(sensors("garden").get("motion"))
        if has_device("garden", "camera"):
            turn("garden", "camera", True, why="giữ an ninh sân vườn")
        if has_device("garden", "light"):
            if active_garden:
                turn("garden", "light", lux < 70, {"power": 45 if lux < 45 else 25}, "đang chăm sân vườn")
            elif night_guard and lux < 18 and motion:
                turn("garden", "light", True, {"power": 25}, "tối và có chuyển động")
            else:
                turn("garden", "light", False, why="không có nhu cầu ra sân")
        if has_device("garden", "pump"):
            if active_garden and soil < 55 and not rain:
                turn("garden", "pump", True, why=f"độ ẩm đất {soil:g}%")
            elif scene == "away" and soil < 28 and not rain:
                turn("garden", "pump", True, why=f"đất quá khô khi vắng nhà ({soil:g}%)")
            else:
                turn("garden", "pump", False, why="không cần tưới lúc này")

    if scene == "sleep":
        state["home_mode"] = "Sleep"
        turn("living_room", "tv", False, why="đi ngủ")
        turn("living_room", "light", False, why="đi ngủ")
        cooling_for("living_room", occupied=False)
        turn("bedroom", "light", True, {"power": 12}, "ánh sáng nhẹ để chuẩn bị ngủ")
        cooling_for("bedroom", occupied=True, quiet=True)
        if has_device("bedroom", "humidifier"):
            hum = value("bedroom", "humidity", 60)
            turn("bedroom", "humidifier", hum < 45, why=f"độ ẩm {hum:g}%")
        if has_device("bedroom", "speaker"):
            turn("bedroom", "speaker", False, why="giảm nhiễu khi ngủ")
        kitchen_safety()
        garden_safety(night_guard=True)

    elif scene == "away":
        state["home_mode"] = "Away"
        for room_id, r in state.get("rooms", {}).items():
            for dev_id in list(r.get("devices", {}).keys()):
                if dev_id not in ["camera", "purifier", "hood", "pump"]:
                    turn(room_id, dev_id, False, why="Away mode tiết kiệm điện")
        for room_id in state.get("rooms", {}):
            air_quality_for(room_id)
        kitchen_safety()
        garden_safety(active_garden=False, night_guard=True)

    elif scene == "movie":
        state["home_mode"] = "Movie"
        # Main need: living room becomes cinema mode.
        turn("living_room", "light", True, {"power": 16}, "xem phim cần ánh sáng dịu")
        turn("living_room", "tv", True, why="xem phim")
        cooling_for("living_room", occupied=True, quiet=True)
        air_quality_for("living_room")
        # Other rooms become low-power because nobody is using them.
        for room_id in ["bedroom"]:
            turn(room_id, "light", False, why="không dùng khi xem phim")
            turn(room_id, "speaker", False, why="tránh nhiễu âm thanh")
            cooling_for(room_id, occupied=False)
            if has_device(room_id, "humidifier"):
                turn(room_id, "humidifier", False, why="không dùng phòng")
        kitchen_safety(movie_snack_mode=True)
        garden_safety(active_garden=False, night_guard=True)

    elif scene == "focus":
        state["home_mode"] = "Focus"
        turn("living_room", "light", True, {"power": 88}, "tập trung cần ánh sáng mạnh")
        turn("living_room", "tv", False, why="giảm xao nhãng")
        cooling_for("living_room", occupied=True)
        air_quality_for("living_room", strong=True)
        # Quiet down other rooms unless environmental safety requires action.
        for room_id in ["bedroom"]:
            turn(room_id, "light", False, why="không phải khu vực focus")
            turn(room_id, "speaker", False, why="giảm xao nhãng")
            cooling_for(room_id, occupied=False)
        kitchen_safety()
        garden_safety(active_garden=False, night_guard=True)

    elif scene == "clean_air":
        state["home_mode"] = "Clean Air"
        for room_id in state.get("rooms", {}):
            air_quality_for(room_id, strong=True)
            # Circulate air only in rooms that are actually dusty or hot.
            pm25 = value(room_id, "pm25", 0)
            temp = value(room_id, "temperature", 28)
            if has_device(room_id, "fan"):
                turn(room_id, "fan", pm25 >= 38 or temp >= 30, {"power": 30}, f"PM2.5 {pm25:g}, nhiệt {temp:g}°C")
        kitchen_safety()
        garden_safety(active_garden=False, night_guard=True)
        # Do not change TVs/speakers unnecessarily in this mode.

    elif scene == "garden":
        state["home_mode"] = "Garden Care"
        garden_safety(active_garden=True, night_guard=True)
        # Indoor rooms become energy-saving while owner checks garden.
        turn("living_room", "tv", False, why="đang chăm sân vườn")
        turn("living_room", "light", False, why="không dùng phòng khách")
        cooling_for("living_room", occupied=False)
        turn("bedroom", "light", False, why="không dùng phòng ngủ")
        cooling_for("bedroom", occupied=False)
        kitchen_safety()

    state["last_scene_plan"] = {
        "scene": scene,
        "label": SCENES[scene]["label"],
        "time": now_iso(),
        "items": plan[:18] if plan else ["Không cần đổi thêm thiết bị, trạng thái hiện tại đã phù hợp."],
    }
    add_event(state, f"AI Smart Scene: {SCENES[scene]['label']}", " • ".join(state["last_scene_plan"]["items"][:8]), "scene")

    if save:
        save_state(state)
    return state


def toggle_automation(rule_id: str, enabled: bool) -> dict[str, Any]:
    state = load_state()
    found = False
    for rule in state.get("automations", []):
        if rule.get("id") == rule_id:
            rule["enabled"] = bool(enabled)
            found = True
            add_event(state, "Cập nhật automation", f"{rule.get('name')} → {'ON' if enabled else 'OFF'}", "automation")
            break
    if not found:
        raise ValueError("Không tìm thấy automation")
    save_state(state)
    return state


def reset_state() -> dict[str, Any]:
    state = default_state()
    add_event(state, "Reset Smart Home", "Khôi phục dữ liệu demo ban đầu", "system")
    save_state(state)
    return state


def normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def canonical_room_id(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    lowered = normalize_text(raw)
    return ROOM_ALIAS.get(lowered) or lowered


def canonical_device_id(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    lowered = normalize_text(raw)
    return DEVICE_ALIAS.get(lowered) or lowered


def local_command_actions(text: str) -> tuple[list[dict[str, Any]], str]:
    """Small fallback parser when Ollama is offline."""
    t = normalize_text(text)
    actions: list[dict[str, Any]] = []
    if any(x in t for x in ["đi ngủ", "sleep"]):
        return [{"type": "scene", "scene": "sleep"}], "Đã hiểu là kích hoạt Sleep Scene."
    if any(x in t for x in ["ra ngoài", "vắng nhà", "away"]):
        return [{"type": "scene", "scene": "away"}], "Đã hiểu là kích hoạt Away Scene."
    if any(x in t for x in ["xem phim", "movie"]):
        return [{"type": "scene", "scene": "movie"}], "Đã hiểu là kích hoạt Movie Scene."
    if any(x in t for x in ["sạch khí", "clean air", "lọc không khí"]):
        return [{"type": "scene", "scene": "clean_air"}], "Đã hiểu là kích hoạt Clean Air."
    if any(x in t for x in ["chăm vườn", "garden care"]):
        return [{"type": "scene", "scene": "garden"}], "Đã hiểu là kích hoạt Garden Care."

    room_id = next((rid for alias, rid in ROOM_ALIAS.items() if alias in t), None)
    device_id = next((did for alias, did in DEVICE_ALIAS.items() if alias in t), None)
    on = True if any(x in t for x in ["bật", "mở", "on"]) else False if any(x in t for x in ["tắt", "off", "đóng"]) else None
    if room_id and device_id and on is not None:
        actions.append({"type": "device", "room_id": room_id, "device_id": device_id, "on": on})
        return actions, f"Đã hiểu là {'bật' if on else 'tắt'} {device_id} ở {room_id}."
    return [], "Mình chưa chắc lệnh này nên chỉ trả lời/gợi ý, chưa tự áp thiết bị."


def apply_actions(actions: list[dict[str, Any]], source: str = "ai") -> tuple[dict[str, Any], list[str]]:
    state = load_state()
    applied: list[str] = []
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        action_type = action.get("type")
        try:
            if action_type == "scene":
                scene = str(action.get("scene", "")).strip().lower()
                if scene in SCENES:
                    apply_scene(scene, state=state, save=False)
                    applied.append(f"Scene: {SCENES[scene]['label']}")
            elif action_type == "device":
                room_id = canonical_room_id(action.get("room_id"))
                device_id = canonical_device_id(action.get("device_id"))
                if room_id in state.get("rooms", {}) and device_id in state["rooms"][room_id].get("devices", {}):
                    patch = action.get("patch") if isinstance(action.get("patch"), dict) else {}
                    set_device(room_id, device_id, on=action.get("on"), patch=patch, state=state, save=False)
                    name = state["rooms"][room_id]["devices"][device_id].get("name", device_id)
                    applied.append(f"{state['rooms'][room_id]['name']}: {name} → {'ON' if state['rooms'][room_id]['devices'][device_id].get('on') else 'OFF'}")
                else:
                    applied.append(f"Không map được thiết bị: room_id={action.get('room_id')} device_id={action.get('device_id')}")
            elif action_type == "home_mode":
                mode = str(action.get("mode") or "Home")[:40]
                state["home_mode"] = mode
                add_event(state, "Cập nhật Home Mode", mode, source)
                applied.append(f"Home Mode: {mode}")
        except Exception as exc:
            applied.append(f"Bỏ qua action lỗi: {exc}")
    if applied:
        apply_basic_automations(state)
        add_event(state, "Áp lệnh từ AI", "; ".join(applied), source)
    save_state(state)
    return state, applied


def build_quick_suggestions(state: dict[str, Any]) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    for room_id, room in state.get("rooms", {}).items():
        s = room.get("sensors", {})
        d = room.get("devices", {})
        name = room.get("name", room_id)
        if s.get("pm25", 0) > 35 and "purifier" in d and not d["purifier"].get("on"):
            suggestions.append({"title": f"Bật lọc khí {name}", "reason": f"PM2.5 đang {s.get('pm25')}", "command": f"bật lọc khí {name.lower()}"})
        if s.get("temperature", 0) > 30 and "fan" in d and not d["fan"].get("on"):
            suggestions.append({"title": f"Bật quạt {name}", "reason": f"Nhiệt độ {s.get('temperature')}°C", "command": f"bật quạt {name.lower()}"})
        if room_id == "garden" and s.get("soil_moisture", 100) < 35 and "pump" in d and not d["pump"].get("on"):
            suggestions.append({"title": "Tưới sân vườn", "reason": f"Độ ẩm đất {s.get('soil_moisture')}%", "command": "bật bơm sân vườn"})
    if not suggestions:
        suggestions.append({"title": "Phân tích bằng AI", "reason": "Nhà đang khá ổn, để AI tìm tối ưu nâng cao", "command": "phân tích nhà hiện tại và gợi ý tiết kiệm điện"})
    return suggestions[:6]



FB_ROOM_TO_API = {
    "phong_khach": "living_room",
    "phong_ngu": "bedroom",
    "nha_bep": "kitchen",
    "san_vuon": "garden",
}

FB_DEVICE_TO_API = {
    "den": "light",
    "quat": "fan",
    "may_lanh": "ac",
    "loc_khi": "purifier",
    "tv": "tv",
    "tao_am": "humidifier",
    "loa": "speaker",
    "hut_mui": "hood",
    "hut_am": "dehumidifier",
    "bom": "pump",
    "camera": "camera",
}

FB_SENSOR_TO_API = {
    "nhiet_do": "temperature",
    "do_am": "humidity",
    "pm25": "pm25",
    "anh_sang": "lux",
    "chuyen_dong": "motion",
    "cua_mo": "door_open",
    "gas_score": "gas_score",
    "do_am_dat": "soil_moisture",
    "mua": "rain",
}


def coerce_firebase_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "on", "1", "yes", "co", "có"}:
            return True
        if lowered in {"false", "off", "0", "no", "khong", "không"}:
            return False
        try:
            n = float(value)
            return int(n) if n.is_integer() else n
        except Exception:
            return value
    return value


def apply_firebase_sync(payload: dict[str, Any]) -> dict[str, Any]:
    """Merge compact Firebase tree into local app state in one atomic pass.

    This endpoint is used by the browser Firebase bridge so Firebase can behave as
    the realtime source for sensors, device on/off, power and target values.
    """
    state = load_state()
    root = payload.get("root") if isinstance(payload.get("root"), dict) else {}
    value_tree = payload.get("value") if isinstance(payload.get("value"), dict) else root.get("value", {})
    command_tree = payload.get("commands") if isinstance(payload.get("commands"), dict) else root.get("commands", {})
    source = str(payload.get("source") or "value")
    mode = payload.get("mode", root.get("mode"))

    if mode:
        state["home_mode"] = str(mode)[:60]

    allowed_sensors = {"temperature", "humidity", "pm25", "lux", "motion", "door_open", "gas_score", "soil_moisture", "rain"}
    changed: list[str] = []

    def apply_value_tree() -> None:
        for fb_room_id, room_payload in (value_tree or {}).items():
            room_id = canonical_room_id(FB_ROOM_TO_API.get(fb_room_id, fb_room_id))
            room = state.get("rooms", {}).get(room_id or "")
            if not room or not isinstance(room_payload, dict):
                continue

            cam_bien = room_payload.get("cam_bien") if isinstance(room_payload.get("cam_bien"), dict) else {}
            sensor_patch: dict[str, Any] = {}
            for fb_key, raw_value in cam_bien.items():
                sensor_key = FB_SENSOR_TO_API.get(fb_key, fb_key)
                if sensor_key in allowed_sensors:
                    sensor_patch[sensor_key] = coerce_firebase_value(raw_value)
            if sensor_patch:
                room.setdefault("sensors", {}).update(sensor_patch)
                changed.append(f"sensor:{room_id}")

            thiet_bi = room_payload.get("thiet_bi") if isinstance(room_payload.get("thiet_bi"), dict) else {}
            for fb_device_id, device_payload in thiet_bi.items():
                device_id = canonical_device_id(FB_DEVICE_TO_API.get(fb_device_id, fb_device_id))
                device = room.get("devices", {}).get(device_id or "")
                if not device or not isinstance(device_payload, dict):
                    continue
                if "on" in device_payload:
                    device["on"] = bool(coerce_firebase_value(device_payload.get("on")))
                for key in ["power", "target", "mode"]:
                    if key in device_payload:
                        device[key] = coerce_firebase_value(device_payload.get(key))
                changed.append(f"device:{room_id}/{device_id}")

    def apply_command_tree() -> None:
        for fb_room_id, devices in (command_tree or {}).items():
            room_id = canonical_room_id(FB_ROOM_TO_API.get(fb_room_id, fb_room_id))
            room = state.get("rooms", {}).get(room_id or "")
            if not room or not isinstance(devices, dict):
                continue
            for fb_device_id, raw_on in devices.items():
                device_id = canonical_device_id(FB_DEVICE_TO_API.get(fb_device_id, fb_device_id))
                device = room.get("devices", {}).get(device_id or "")
                if not device:
                    continue
                device["on"] = bool(coerce_firebase_value(raw_on))
                changed.append(f"command:{room_id}/{device_id}")

    # If user edited commands, command values should win over stale value/on.
    # If user edited value/thiet_bi/on, value should win over stale commands.
    if source == "commands":
        apply_value_tree()
        apply_command_tree()
    else:
        apply_command_tree()
        apply_value_tree()

    applied_rules = []
    if changed:
        # Firebase can be the realtime source for sensors. After merging sensor
        # values, Smart Notes must execute immediately; otherwise UI may show
        # 35°C while note devices stay OFF.
        applied_rules = apply_user_rules(state)
        msg = f"{len(changed)} thay đổi từ {source}"
        if applied_rules:
            msg += f"; áp dụng {len(applied_rules)} smart note"
        add_event(state, "Đồng bộ Firebase", msg, "firebase")
    save_state(state)
    return state


# ---------------- HomeOS v13: rules, alerts, energy insights ----------------

SAFE_METRICS = {
    "temperature", "humidity", "pm25", "lux", "gas_score", "soil_moisture", "motion", "door_open", "rain"
}

OPERATORS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def compare_values(left: Any, op: str, right: Any) -> bool:
    op = op if op in OPERATORS else ">="
    left = coerce_firebase_value(left)
    right = coerce_firebase_value(right)
    if isinstance(left, bool) or isinstance(right, bool):
        return OPERATORS[op](bool(left), bool(right))
    try:
        return OPERATORS[op](float(left), float(right))
    except Exception:
        return OPERATORS[op](str(left), str(right))


def normalize_rule(payload: dict[str, Any]) -> dict[str, Any]:
    rule = dict(payload or {})
    rule_id = str(rule.get("id") or f"rule_{uuid4().hex[:8]}")
    room_id = canonical_room_id(rule.get("room_id")) or "living_room"
    metric = str(rule.get("metric") or "temperature").strip()
    if metric not in SAFE_METRICS:
        metric = "temperature"
    operator = str(rule.get("operator") or ">=").strip()
    if operator not in OPERATORS:
        operator = ">="
    action = rule.get("action") if isinstance(rule.get("action"), dict) else {}
    action_type = action.get("type") or "device"
    if action_type == "device":
        action = {
            "type": "device",
            "room_id": canonical_room_id(action.get("room_id") or room_id) or room_id,
            "device_id": canonical_device_id(action.get("device_id")) or "fan",
            "on": bool(coerce_firebase_value(action.get("on", True))),
            "patch": action.get("patch") if isinstance(action.get("patch"), dict) else {},
        }
    elif action_type == "scene":
        action = {"type": "scene", "scene": str(action.get("scene") or "comfort")}
    else:
        action = {"type": "none"}

    return {
        "id": rule_id,
        "name": str(rule.get("name") or "Luật tự động mới")[:80],
        "enabled": bool(rule.get("enabled", True)),
        "room_id": room_id,
        "metric": metric,
        "operator": operator,
        "value": coerce_firebase_value(rule.get("value", 0)),
        "action": action,
    }


def upsert_user_rule(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    rule = normalize_rule(payload)
    rules = state.setdefault("user_rules", [])
    for idx, existing in enumerate(rules):
        if existing.get("id") == rule["id"]:
            rules[idx] = rule
            add_event(state, "Cập nhật user rule", rule["name"], "rule")
            save_state(state)
            return state
    rules.append(rule)
    add_event(state, "Tạo user rule", rule["name"], "rule")
    save_state(state)
    return state


def toggle_user_rule(rule_id: str, enabled: bool) -> dict[str, Any]:
    state = load_state()
    found = False
    for rule in state.setdefault("user_rules", []):
        if rule.get("id") == rule_id:
            rule["enabled"] = bool(enabled)
            found = True
            add_event(state, "Bật/tắt user rule", f"{rule.get('name')} → {'ON' if enabled else 'OFF'}", "rule")
            break
    if not found:
        raise ValueError("Không tìm thấy user rule")
    save_state(state)
    return state


def delete_user_rule(rule_id: str) -> dict[str, Any]:
    state = load_state()
    before = len(state.setdefault("user_rules", []))
    state["user_rules"] = [r for r in state["user_rules"] if r.get("id") != rule_id]
    if len(state["user_rules"]) == before:
        raise ValueError("Không tìm thấy user rule")
    add_event(state, "Xóa user rule", rule_id, "rule")
    save_state(state)
    return state


def apply_user_rules(state: dict[str, Any]) -> list[str]:
    applied: list[str] = []
    for rule in state.get("user_rules", []):
        if not rule.get("enabled", True):
            continue
        room_id = canonical_room_id(rule.get("room_id"))
        room = state.get("rooms", {}).get(room_id or "")
        if not room:
            continue
        metric = str(rule.get("metric") or "temperature")
        current = room.get("sensors", {}).get(metric)
        if not compare_values(current, str(rule.get("operator") or ">="), rule.get("value")):
            continue
        action = rule.get("action") if isinstance(rule.get("action"), dict) else {}
        if action.get("type") == "device":
            target_room = canonical_room_id(action.get("room_id") or room_id)
            device_id = canonical_device_id(action.get("device_id"))
            device = state.get("rooms", {}).get(target_room or "", {}).get("devices", {}).get(device_id or "")
            if not device:
                continue
            if action.get("on") is not None:
                device["on"] = bool(action.get("on"))
            patch = action.get("patch") if isinstance(action.get("patch"), dict) else {}
            for k, v in patch.items():
                if k not in {"name", "icon"}:
                    device[k] = v
            if "set_manual_override" in globals():
                set_manual_override(state, target_room, device_id, reason="smart-note", ttl_minutes=90)
            applied.append(f"{rule.get('name')}: {state['rooms'][target_room]['name']} / {device.get('name', device_id)}")
        elif action.get("type") == "scene":
            scene = str(action.get("scene") or "").lower()
            if scene in SCENES:
                apply_scene(scene, state=state, save=False)
                applied.append(f"{rule.get('name')}: Scene {scene}")
    if applied:
        add_event(state, "User Rules áp dụng", "; ".join(applied[-6:]), "rule")
    return applied


def generate_alerts(state: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for room_id, room in state.get("rooms", {}).items():
        name = room.get("name", room_id)
        s = room.get("sensors", {})
        temp = _to_float(s.get("temperature"), 0)
        hum = _to_float(s.get("humidity"), 0)
        pm = _to_float(s.get("pm25"), 0)
        gas = _to_float(s.get("gas_score"), 0)
        soil = s.get("soil_moisture")
        if temp >= 34:
            alerts.append({"level": "danger", "room_id": room_id, "title": f"{name} quá nóng", "detail": f"Nhiệt độ {temp:g}°C, nên bật máy lạnh hoặc quạt mạnh."})
        elif temp >= 31:
            alerts.append({"level": "warning", "room_id": room_id, "title": f"{name} hơi nóng", "detail": f"Nhiệt độ {temp:g}°C, nên dùng quạt trước để tiết kiệm điện."})
        if hum >= 82:
            alerts.append({"level": "warning", "room_id": room_id, "title": f"{name} ẩm cao", "detail": f"Độ ẩm {hum:g}%, nên bật hút ẩm nếu có."})
        if pm >= 55:
            alerts.append({"level": "danger", "room_id": room_id, "title": f"{name} PM2.5 cao", "detail": f"PM2.5 {pm:g}, nên bật lọc khí/hút mùi."})
        elif pm >= 38:
            alerts.append({"level": "warning", "room_id": room_id, "title": f"{name} chất lượng khí cần chú ý", "detail": f"PM2.5 {pm:g}."})
        if gas >= 35:
            alerts.append({"level": "danger", "room_id": room_id, "title": "Bếp cần thông gió", "detail": f"Gas score {gas:g}, nên bật hút mùi và kiểm tra bếp."})
        if soil is not None and _to_float(soil, 100) < 30:
            alerts.append({"level": "warning", "room_id": room_id, "title": "Sân vườn khô", "detail": f"Độ ẩm đất {_to_float(soil):g}%, nên bật bơm nếu không mưa."})
        if state.get("home_mode", "").lower().startswith("away") and s.get("motion"):
            alerts.append({"level": "danger", "room_id": room_id, "title": f"Có chuyển động khi Away", "detail": f"Phát hiện chuyển động ở {name}."})
    return alerts[:12]


def compute_energy_optimization(state: dict[str, Any]) -> dict[str, Any]:
    energy = estimate_energy(state)
    active = energy.get("active_devices", [])
    tips: list[str] = []
    for item in sorted(active, key=lambda x: x.get("watts", 0), reverse=True)[:6]:
        room_name = item.get("room")
        device_name = item.get("name")
        watts = item.get("watts", 0)
        tips.append(f"{room_name}: {device_name} đang dùng khoảng {watts}W.")
    if any("Máy lạnh" in item.get("name", "") for item in active):
        tips.append("Có máy lạnh đang chạy: tăng target lên 26°C và bật quạt hỗ trợ thường tiết kiệm hơn.")
    if energy.get("total_w", 0) > 900:
        tips.append("Tổng tải đang cao, nên kiểm tra máy lạnh/thiết bị công suất lớn.")
    if not tips:
        tips.append("Điện năng hiện ổn. Không có thiết bị nào tiêu thụ quá cao.")
    return {
        "total_w": energy.get("total_w", 0),
        "estimated_kwh_day": energy.get("estimated_kwh_day", 0),
        "estimated_cost_day_vnd": energy.get("estimated_cost_day_vnd", 0),
        "top_devices": sorted(active, key=lambda x: x.get("watts", 0), reverse=True)[:8],
        "tips": tips[:8],
    }


def run_homeos_tick(profile: str = "comfort") -> dict[str, Any]:
    state = load_state()
    apply_comfort_engine(state, profile=profile, force=True, source="homeos")
    apply_user_rules(state)
    state["alerts"] = generate_alerts(state)
    add_event(state, "HomeOS Tick", f"profile={profile}, alerts={len(state['alerts'])}", "homeos")
    save_state(state)
    return state




# ---------------- Practical v15: AI Smart Bubble Notes ----------------

def extract_first_number(text: str, default: float) -> float:
    match = re.search(r"(\d+(?:[\\.,]\d+)?)", text or "")
    if not match:
        return default
    try:
        value = float(match.group(1).replace(",", "."))
        return value
    except Exception:
        return default


def extract_number_after_keywords(text: str, keywords: list[str], default: float) -> float:
    t = normalize_text(text)
    for kw in keywords:
        idx = t.find(kw)
        if idx != -1:
            sub = t[idx:idx + 60]
            match = re.search(r"(\d+(?:[\\.,]\d+)?)", sub)
            if match:
                try:
                    return float(match.group(1).replace(",", "."))
                except Exception:
                    pass
    return default


def infer_room_from_text(text: str) -> str:
    t = normalize_text(text)
    for alias, room_id in ROOM_ALIAS.items():
        if alias in t:
            return room_id
    if "bếp" in t or "bep" in t or "mùi" in t or "gas" in t:
        return "kitchen"
    if "ngủ" in t or "ngu" in t:
        return "bedroom"
    if "sân" in t or "vườn" in t or "vuon" in t:
        return "garden"
    return "living_room"


def make_smart_rule(name: str, room_id: str, metric: str, operator: str, value: Any, device_id: str, on: bool = True, patch: dict[str, Any] | None = None, note_id: str | None = None) -> dict[str, Any]:
    rule = normalize_rule({
        "id": f"{note_id}_{device_id}_{metric}" if note_id else f"rule_{uuid4().hex[:8]}",
        "name": name,
        "enabled": True,
        "room_id": room_id,
        "metric": metric,
        "operator": operator,
        "value": value,
        "action": {
            "type": "device",
            "room_id": room_id,
            "device_id": device_id,
            "on": on,
            "patch": patch or {},
        },
    })
    return rule



def extract_condition_temperature(text: str, default: float = 31.0) -> float:
    """Extract trigger temperature, e.g. 'khi nhiệt độ 32 độ' -> 32."""
    t = normalize_text(text)
    patterns = [
        r"(?:khi|neu|nếu).{0,36}?(?:nhiet do|nhiệt độ|nong|nóng|lanh|lạnh|duoi|dưới|thap hon|thấp hơn|nho hon|nhỏ hơn|tren|trên|tu|từ|>=|<=|>|<).{0,24}?(\d+(?:[\.,]\d+)?)",
        r"(?:nhiet do|nhiệt độ|nong|nóng|lanh|lạnh|duoi|dưới|thap hon|thấp hơn|nho hon|nhỏ hơn|tren|trên|tu|từ|>=|<=|>|<).{0,24}?(\d+(?:[\.,]\d+)?)",
        r"[<>]=?\s*(\d+(?:[\.,]\d+)?)",
    ]
    for pattern in patterns:
        m = re.search(pattern, t)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except Exception:
                pass
    nums = numbers_in_text(t) if "numbers_in_text" in globals() else []
    if nums:
        # For note conditions, a single number is usually the trigger threshold.
        return float(nums[-1])
    return default


def extract_ac_target_from_note(text: str, condition_temp: float, default: int = 26) -> int:
    """Extract AC target only when user clearly asks target/setpoint.

    Avoid the old bug: 'bật máy lạnh khi nhiệt độ 32 độ' used 32 as AC target,
    then clamped it to 28. Here 32 is treated as condition, not target.
    """
    t = normalize_text(text)
    explicit_patterns = [
        r"(?:target|dat|đặt|de|để|cai|cài|xuong|xuống|muc|mức).{0,18}?(\d+(?:[\.,]\d+)?)",
        r"(?:may lanh|máy lạnh|dieu hoa|điều hòa).{0,20}?(\d+(?:[\.,]\d+)?)\s*(?:do|độ|c)",
    ]
    for pattern in explicit_patterns:
        for m in re.finditer(pattern, t):
            try:
                value = float(m.group(1).replace(",", "."))
            except Exception:
                continue
            if 18 <= value <= 30 and abs(value - condition_temp) > 0.25:
                return int(round(value))

    nums = numbers_in_text(t) if "numbers_in_text" in globals() else []
    valid_targets = [n for n in nums if 18 <= n <= 30 and abs(n - condition_temp) > 0.25]
    # If there are at least two useful numbers, prefer the first setpoint-like number.
    if len(nums) >= 2 and valid_targets:
        return int(round(valid_targets[0]))
    return int(default)


def note_mentions_device(text: str, device_id: str) -> bool:
    t = normalize_text(text)
    if device_id == "ac":
        return any(x in t for x in ["may lanh", "máy lạnh", "dieu hoa", "điều hòa", "ac"])
    if device_id == "fan":
        return any(x in t for x in ["quat", "quạt", "fan"])
    if device_id == "light":
        return any(x in t for x in ["den", "đèn"])
    if device_id == "purifier":
        return any(x in t for x in ["loc khi", "lọc khí", "loc_khi", "lọc khí mini", "loc khi mini", "purifier"])
    if device_id == "hood":
        return any(x in t for x in ["hut mui", "hút mùi", "hood", "quạt hút", "quat hut"])
    if device_id == "dehumidifier":
        return any(x in t for x in ["hut am", "hút ẩm", "may hut am", "máy hút ẩm"])
    if device_id == "humidifier":
        return any(x in t for x in ["tao am", "tạo ẩm", "may tao am", "máy tạo ẩm"])
    if device_id == "pump":
        return any(x in t for x in ["bom", "bơm", "may bom", "máy bơm"])
    if device_id == "camera":
        return "camera" in t
    return device_id in t


def explicit_note_device(text: str) -> str | None:
    # Order matters: dehumidifier before humidifier, hood before generic air words.
    for device_id in ["dehumidifier", "humidifier", "purifier", "hood", "ac", "fan", "light", "pump", "camera"]:
        if note_mentions_device(text, device_id):
            return device_id
    return None


def metric_from_note(text: str, device_id: str | None = None) -> tuple[str, str, float]:
    t = normalize_text(text)
    if any(x in t for x in ["pm2.5", "pm 2.5", "pm25", "pm", "bụi", "bui"]):
        return "pm25", "PM2.5", 38.0
    if "gas" in t:
        return "gas_score", "gas", 30.0
    if any(x in t for x in ["do am dat", "độ ẩm đất", "dat", "đất"]):
        return "soil_moisture", "độ ẩm đất", 30.0
    if any(x in t for x in ["do am", "độ ẩm", "am", "ẩm"]):
        return "humidity", "độ ẩm", 78.0 if device_id == "dehumidifier" else 40.0
    if any(x in t for x in ["anh sang", "ánh sáng", "lux"]):
        return "lux", "ánh sáng", 30.0
    return "temperature", "nhiệt độ", 31.0


def extract_metric_threshold(text: str, metric: str, default: float) -> float:
    t = normalize_text(text)
    # Avoid taking the 2.5 inside the metric name PM2.5 as the threshold.
    metric_patterns = {
        "pm25": [
            r"(?:pm\s*2[\.,]?5|pm25|pm|bui|bụi).{0,36}?(?:nho hon|nhỏ hơn|be hon|bé hơn|duoi|dưới|lon hon|lớn hơn|tren|trên|>=|<=|>|<).{0,12}?(\d+(?:[\.,]\d+)?)",
            r"(?:nho hon|nhỏ hơn|be hon|bé hơn|duoi|dưới|lon hon|lớn hơn|tren|trên|>=|<=|>|<).{0,12}?(\d+(?:[\.,]\d+)?).{0,24}?(?:pm\s*2[\.,]?5|pm25|pm|bui|bụi)",
        ],
        "gas_score": [r"gas.{0,30}?(\d+(?:[\.,]\d+)?)"],
        "soil_moisture": [r"(?:do am dat|độ ẩm đất|dat|đất).{0,36}?(\d+(?:[\.,]\d+)?)"],
        "humidity": [r"(?:do am|độ ẩm|am|ẩm).{0,36}?(\d+(?:[\.,]\d+)?)"],
        "lux": [r"(?:anh sang|ánh sáng|lux).{0,36}?(\d+(?:[\.,]\d+)?)"],
    }
    if metric == "temperature":
        return extract_condition_temperature(text, default)
    for pattern in metric_patterns.get(metric, []):
        m = re.search(pattern, t)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except Exception:
                pass
    nums = numbers_in_text(t) if "numbers_in_text" in globals() else []
    if nums:
        if metric == "pm25":
            # Drop 2.5 if it is merely part of "PM2.5" and another number exists.
            filtered = [n for n in nums if abs(n - 2.5) > 0.0001]
            if filtered:
                return float(filtered[-1])
        return float(nums[-1])
    return default


def condition_phrase_for_metric(metric_label: str, operator: str, value: float) -> str:
    if metric_label == "nhiệt độ":
        return condition_phrase(operator, value)
    if operator == "<":
        return f"{metric_label} dưới {value:g}"
    if operator == "<=":
        return f"{metric_label} tối đa {value:g}"
    if operator == ">":
        return f"{metric_label} trên {value:g}"
    return f"{metric_label} từ {value:g}"


def device_vn_name(device_id: str) -> str:
    return {
        "ac": "máy lạnh",
        "fan": "quạt",
        "light": "đèn",
        "purifier": "lọc khí",
        "hood": "hút mùi",
        "dehumidifier": "hút ẩm",
        "humidifier": "tạo ẩm",
        "pump": "máy bơm",
        "camera": "camera",
    }.get(device_id, device_id)






def infer_note_action(text: str) -> bool:
    """True = turn on, False = turn off for a note action."""
    t = normalize_text(text)
    off_words = ["tat", "tắt", "off", "dong", "đóng", "ngung", "ngừng", "dung", "dừng"]
    on_words = ["bat", "bật", "mo", "mở", "on", "chay", "chạy"]
    first_off = min([t.find(w) for w in off_words if w in t] or [10**9])
    first_on = min([t.find(w) for w in on_words if w in t] or [10**9])
    if first_off < first_on:
        return False
    return True


def infer_condition_operator(text: str) -> tuple[str, str]:
    """Return (operator, label) for the condition phrase."""
    t = normalize_text(text)
    if any(x in t for x in ["duoi", "dưới", "nho hon", "nhỏ hơn", "be hon", "bé hơn", "thap hon", "thấp hơn", "<"]):
        if any(x in t for x in ["<=", "be hon hoac bang", "bé hơn hoặc bằng", "nhỏ hơn hoặc bằng", "duoi hoac bang", "dưới hoặc bằng"]):
            return "<=", "từ tối đa"
        return "<", "dưới"
    if any(x in t for x in ["tren", "trên", "lon hon", "lớn hơn", "cao hon", "cao hơn", ">"]):
        if any(x in t for x in [">=", "lon hon hoac bang", "lớn hơn hoặc bằng", "tren hoac bang", "trên hoặc bằng"]):
            return ">=", "từ"
        return ">", "trên"
    return ">=", "từ"


def condition_phrase(operator: str, value: float) -> str:
    if operator == "<":
        return f"dưới {value:g}°C"
    if operator == "<=":
        return f"tối đa {value:g}°C"
    if operator == ">":
        return f"trên {value:g}°C"
    return f"từ {value:g}°C"


def action_phrase(on: bool, device_name: str, suffix: str = "") -> str:
    verb = "bật" if on else "tắt"
    return f"{verb} {device_name}{suffix}"


def smart_note_plan_from_text(text: str) -> dict[str, Any]:
    """Convert a natural-language note into practical hidden rules.

    It is intentionally deterministic so it still works if Ollama is offline.
    """
    raw = str(text or "").strip()
    t = normalize_text(raw)
    room_id = infer_room_from_text(t)
    room_label = ROOM_ALIAS.get(room_id, room_id)
    note_id = f"note_{uuid4().hex[:8]}"
    rules: list[dict[str, Any]] = []
    summary_parts: list[str] = []

    wants_disable = any(x in t for x in ["tắt note", "xóa note", "xoá note", "hủy note", "huy note", "disable note"])
    if wants_disable:
        return {
            "mode": "disable",
            "room_id": room_id,
            "note_id": note_id,
            "title": "Tắt smart note",
            "summary": "Mình sẽ tắt các note phù hợp nếu tìm thấy.",
            "rules": [],
        }

    # If the user names a concrete device (lọc khí, hút mùi, máy lạnh, quạt...),
    # obey exactly that device/action/condition and DO NOT add extra inferred rules.
    explicit_device_id = explicit_note_device(t)
    if explicit_device_id:
        metric, metric_label, default_threshold = metric_from_note(t, explicit_device_id)
        operator, _op_label = infer_condition_operator(t)
        threshold = extract_metric_threshold(t, metric, default_threshold)
        action_on = infer_note_action(t)

        patch: dict[str, Any] = {}
        if explicit_device_id == "ac" and action_on:
            patch["target"] = extract_ac_target_from_note(t, threshold if metric == "temperature" else -999, default=26)
        if explicit_device_id in {"fan", "light", "hood"}:
            power = extract_number_after_keywords(t, ["cong suat", "công suất", "power", "%"], -1)
            if power >= 0:
                patch["power"] = int(max(0, min(100, power)))
            elif action_on:
                if explicit_device_id == "hood":
                    patch["power"] = 75 if any(x in t for x in ["manh", "mạnh", "cao"]) else 45
                elif explicit_device_id == "fan":
                    patch["power"] = 45
                elif explicit_device_id == "light":
                    patch["power"] = 70

        device_name = device_vn_name(explicit_device_id)
        cond_text = condition_phrase_for_metric(metric_label, operator, threshold)
        suffix = ""
        if explicit_device_id == "ac" and action_on and "target" in patch:
            suffix = f" {patch['target']}°C"
        elif "power" in patch:
            suffix = f" {patch['power']}%"

        if explicit_device_id in default_state()["rooms"].get(room_id, {}).get("devices", {}):
            rules.append(make_smart_rule(
                f"{ROOM_ALIAS.get(room_id, room_id)} {cond_text} thì {'bật' if action_on else 'tắt'} {device_name}",
                room_id, metric, operator, threshold, explicit_device_id, action_on, patch, note_id,
            ))
            summary_parts.append(f"{cond_text} {action_phrase(action_on, device_name, suffix)}")
            return {
                "mode": "upsert",
                "room_id": room_id,
                "note_id": note_id,
                "title": raw[:80] or "Smart note",
                "summary": "; ".join(summary_parts),
                "rules": rules,
            }

    hot_words = ["nóng", "nong", "làm mát", "lam mat", "mát", "mat", "máy lạnh", "may lanh", "quạt", "quat"]
    humid_high_words = ["ẩm cao", "am cao", "hút ẩm", "hut am", "nồm", "nom"]
    dry_words = ["khô", "kho", "tạo ẩm", "tao am"]
    air_words = ["pm", "bụi", "bui", "lọc khí", "loc khi", "không khí", "khong khi"]
    kitchen_words = ["gas", "mùi", "mui", "hút mùi", "hut mui"]
    garden_words = ["đất", "dat", "tưới", "tuoi", "bơm", "bom", "vườn", "vuon"]

    # Default smart intent: hot/cooling if user says note but no specific metric.
    is_hot = any(x in t for x in hot_words) or ("note" in t and room_id in {"bedroom", "living_room"})
    is_humid_high = any(x in t for x in humid_high_words)
    is_dry = any(x in t for x in dry_words)
    is_air = any(x in t for x in air_words)
    is_kitchen = room_id == "kitchen" and any(x in t for x in kitchen_words)
    is_garden = room_id == "garden" and any(x in t for x in garden_words)

    if is_hot:
        threshold = extract_condition_temperature(t, 31.0)
        operator, _op_label = infer_condition_operator(t)
        action_on = infer_note_action(t)
        explicit_ac = note_mentions_device(t, "ac")
        explicit_fan = note_mentions_device(t, "fan")
        explicit_light = note_mentions_device(t, "light")
        target = extract_ac_target_from_note(t, threshold, default=26)
        power = extract_number_after_keywords(t, ["công suất", "cong suat", "power", "%", "quạt", "quat"], 45.0 if threshold >= 31 else 35.0)
        power = int(max(20, min(85, power)))
        target = int(max(18, min(30, target)))

        available_devices = default_state()["rooms"].get(room_id, {}).get("devices", {})
        cond = condition_phrase(operator, threshold)

        if explicit_ac:
            # User explicitly said máy lạnh, so obey the action and operator exactly.
            if "ac" in available_devices:
                patch = {"target": target} if action_on else {}
                rules.append(make_smart_rule(
                    f"{ROOM_ALIAS.get(room_id, room_id)} {cond} thì {'bật' if action_on else 'tắt'} máy lạnh",
                    room_id, "temperature", operator, threshold, "ac", action_on, patch, note_id,
                ))
                suffix = f" {target}°C" if action_on else ""
                summary_parts.append(f"{cond} {action_phrase(action_on, 'máy lạnh', suffix)}")
            if explicit_fan and "fan" in available_devices:
                rules.append(make_smart_rule(
                    f"{ROOM_ALIAS.get(room_id, room_id)} {cond} thì {'bật' if action_on else 'tắt'} quạt hỗ trợ",
                    room_id, "temperature", operator, threshold, "fan", action_on, {"power": power} if action_on else {}, note_id,
                ))
                suffix = f" {power}%" if action_on else ""
                summary_parts.append(f"{cond} {action_phrase(action_on, 'quạt', suffix)}")
        elif explicit_fan:
            if "fan" in available_devices:
                rules.append(make_smart_rule(
                    f"{ROOM_ALIAS.get(room_id, room_id)} {cond} thì {'bật' if action_on else 'tắt'} quạt",
                    room_id, "temperature", operator, threshold, "fan", action_on, {"power": power} if action_on else {}, note_id,
                ))
                suffix = f" {power}%" if action_on else ""
                summary_parts.append(f"{cond} {action_phrase(action_on, 'quạt', suffix)}")
        else:
            # Vague note like "phòng ngủ nóng thì ưu tiên làm mát": fan-first + AC later.
            # But if the user says "tắt ... dưới X" without device, cooling devices are turned off.
            if not action_on and operator in {"<", "<="}:
                if "fan" in available_devices:
                    rules.append(make_smart_rule(
                        f"{ROOM_ALIAS.get(room_id, room_id)} {cond} thì tắt quạt",
                        room_id, "temperature", operator, threshold, "fan", False, {}, note_id,
                    ))
                    summary_parts.append(f"{cond} tắt quạt")
                if "ac" in available_devices:
                    rules.append(make_smart_rule(
                        f"{ROOM_ALIAS.get(room_id, room_id)} {cond} thì tắt máy lạnh",
                        room_id, "temperature", operator, threshold, "ac", False, {}, note_id,
                    ))
                    summary_parts.append(f"{cond} tắt máy lạnh")
            else:
                if "fan" in available_devices:
                    rules.append(make_smart_rule(
                        f"{ROOM_ALIAS.get(room_id, room_id)} nóng thì bật quạt",
                        room_id, "temperature", ">=", threshold, "fan", True, {"power": power}, note_id,
                    ))
                    summary_parts.append(f"từ {threshold:g}°C bật quạt {power}%")
                ac_threshold = max(threshold + 1.0, 32.0)
                if "ac" in available_devices:
                    rules.append(make_smart_rule(
                        f"{ROOM_ALIAS.get(room_id, room_id)} rất nóng thì bật máy lạnh",
                        room_id, "temperature", ">=", ac_threshold, "ac", True, {"target": target}, note_id,
                    ))
                    summary_parts.append(f"từ {ac_threshold:g}°C bật máy lạnh {target}°C")

    if is_humid_high:
        threshold = extract_number_after_keywords(t, ["độ ẩm", "do am", "ẩm", "am"], 78.0)
        if "dehumidifier" in default_state()["rooms"].get(room_id, {}).get("devices", {}):
            rules.append(make_smart_rule(
                f"{ROOM_ALIAS.get(room_id, room_id)} ẩm cao thì hút ẩm",
                room_id, "humidity", ">=", threshold, "dehumidifier", True, {}, note_id,
            ))
            summary_parts.append(f"độ ẩm từ {threshold:g}% bật hút ẩm")

    if is_dry:
        threshold = extract_number_after_keywords(t, ["độ ẩm", "do am", "khô", "kho"], 40.0)
        if "humidifier" in default_state()["rooms"].get(room_id, {}).get("devices", {}):
            rules.append(make_smart_rule(
                f"{ROOM_ALIAS.get(room_id, room_id)} khô thì tạo ẩm",
                room_id, "humidity", "<=", threshold, "humidifier", True, {}, note_id,
            ))
            summary_parts.append(f"độ ẩm dưới {threshold:g}% bật tạo ẩm")

    if is_air:
        threshold = extract_number_after_keywords(t, ["pm2.5", "pm", "bụi", "bui"], 38.0)
        if "purifier" in default_state()["rooms"].get(room_id, {}).get("devices", {}):
            rules.append(make_smart_rule(
                f"{ROOM_ALIAS.get(room_id, room_id)} PM2.5 cao thì lọc khí",
                room_id, "pm25", ">=", threshold, "purifier", True, {}, note_id,
            ))
            summary_parts.append(f"PM2.5 từ {threshold:g} bật lọc khí")

    if is_kitchen:
        gas_threshold = extract_number_after_keywords(t, ["gas"], 30.0)
        power = int(max(45, min(90, extract_number_after_keywords(t, ["công suất", "cong suat", "hút mùi", "hut mui"], 75.0))))
        if "hood" in default_state()["rooms"].get("kitchen", {}).get("devices", {}):
            rules.append(make_smart_rule(
                "Bếp có gas/mùi thì bật hút mùi",
                "kitchen", "gas_score", ">=", gas_threshold, "hood", True, {"power": power}, note_id,
            ))
            summary_parts.append(f"gas từ {gas_threshold:g} bật hút mùi {power}%")

    if is_garden:
        threshold = extract_number_after_keywords(t, ["đất", "dat", "ẩm", "am"], 30.0)
        if "pump" in default_state()["rooms"].get("garden", {}).get("devices", {}):
            rules.append(make_smart_rule(
                "Sân vườn khô thì bật bơm",
                "garden", "soil_moisture", "<=", threshold, "pump", True, {}, note_id,
            ))
            summary_parts.append(f"độ ẩm đất dưới {threshold:g}% bật bơm")

    if not rules:
        # Safe default note.
        threshold = 31.0
        rules.append(make_smart_rule(
            f"{ROOM_ALIAS.get(room_id, room_id)} nóng thì bật quạt",
            room_id, "temperature", ">=", threshold, "fan", True, {"power": 40}, note_id,
        ))
        summary_parts.append("mặc định: nóng từ 31°C bật quạt 40%")

    return {
        "mode": "upsert",
        "room_id": room_id,
        "note_id": note_id,
        "title": raw[:80] or "Smart note",
        "summary": "; ".join(summary_parts),
        "rules": rules,
    }


def create_smart_note_from_text(text: str) -> dict[str, Any]:
    state = load_state()
    plan = smart_note_plan_from_text(text)

    if plan.get("mode") == "disable":
        target_room = plan.get("room_id")
        changed = 0
        for note in state.setdefault("smart_notes", []):
            if note.get("room_id") == target_room:
                note["enabled"] = False
                changed += 1
        for rule in state.setdefault("user_rules", []):
            if rule.get("room_id") == target_room:
                rule["enabled"] = False
        add_event(state, "AI Smart Bubble", f"Tắt {changed} note ở {target_room}", "ai")
        save_state(state)
        return {
            "state": state,
            "note": None,
            "reply": f"Mình đã tắt các smart note liên quan tới {target_room}.",
            "created_rules": [],
        }

    # Multiple notes in the same room must be allowed:
    # e.g. ON AC when temp > 33°C and OFF AC when temp < 28°C.
    # Only disable older generated notes when the user clearly asks to edit/sửa/thay note.
    room_id = plan["room_id"]
    is_update_note = any(x in normalize_text(text) for x in ["sua note", "sửa note", "thay note", "cap nhat note", "cập nhật note"])
    if is_update_note:
        for note in state.setdefault("smart_notes", []):
            if note.get("room_id") == room_id and note.get("enabled", True):
                note["enabled"] = False
        for rule in state.setdefault("user_rules", []):
            if str(rule.get("id", "")).startswith("note_") and rule.get("room_id") == room_id:
                rule["enabled"] = False

    note = {
        "id": plan["note_id"],
        "title": plan["title"],
        "summary": plan["summary"],
        "room_id": room_id,
        "enabled": True,
        "rule_ids": [r["id"] for r in plan["rules"]],
        "created_at": now_iso(),
    }
    state.setdefault("smart_notes", []).append(note)
    state.setdefault("user_rules", []).extend(plan["rules"])
    add_event(state, "AI Smart Bubble tạo note", note["summary"], "ai")
    apply_user_rules(state)
    save_state(state)

    reply = f"Mình đã tạo smart note: {note['summary']}."
    return {"state": state, "note": note, "reply": reply, "created_rules": plan["rules"]}


def toggle_smart_note(note_id: str, enabled: bool) -> dict[str, Any]:
    state = load_state()
    found = False
    for note in state.setdefault("smart_notes", []):
        if note.get("id") == note_id:
            note["enabled"] = bool(enabled)
            found = True
            rule_ids = set(note.get("rule_ids", []))
            for rule in state.setdefault("user_rules", []):
                if rule.get("id") in rule_ids:
                    rule["enabled"] = bool(enabled)
            add_event(state, "Cập nhật smart note", f"{note.get('title')} → {'ON' if enabled else 'OFF'}", "ai")
            break
    if not found:
        raise ValueError("Không tìm thấy smart note")
    save_state(state)
    return state


def delete_smart_note(note_id: str) -> dict[str, Any]:
    state = load_state()
    target = None
    for note in state.setdefault("smart_notes", []):
        if note.get("id") == note_id:
            target = note
            break
    if not target:
        raise ValueError("Không tìm thấy smart note")
    rule_ids = set(target.get("rule_ids", []))
    state["smart_notes"] = [n for n in state.get("smart_notes", []) if n.get("id") != note_id]
    state["user_rules"] = [r for r in state.get("user_rules", []) if r.get("id") not in rule_ids]
    add_event(state, "Xóa smart note", target.get("title", note_id), "ai")
    save_state(state)
    return state



# ---------------- v16: AI Smart Chat actions beyond notes ----------------

def detect_intent_from_text(text: str) -> str:
    t = normalize_text(text)
    if any(x in t for x in ["tạo note", "tao note", "note ", "ghi nhớ", "ghi nho", "khi nào", "nếu ", "neu ", "sửa note", "sua note", "tắt note", "tat note", "xóa note", "xoá note"]):
        return "note"
    if any(x in t for x in ["tối ưu", "toi uu", "optimize", "run homeos", "homeos", "auto mode", "eco", "comfort", "sleep", "movie", "away", "guest", "đi ngủ", "di ngu", "xem phim", "vắng nhà", "vang nha"]):
        return "auto"
    if any(x in t for x in ["tình trạng", "tinh trang", "trạng thái", "trang thai", "nhà sao", "nha sao", "đang thế nào", "dang the nao", "status"]):
        return "status"
    if any(x in t for x in ["điện", "dien", "energy", "tiền điện", "tien dien", "tốn điện", "ton dien"]):
        return "energy"
    if any(x in t for x in ["cảnh báo", "canh bao", "alert", "nguy hiểm", "nguy hiem"]):
        return "alerts"
    if any(x in t for x in ["bật", "bat", "mở", "mo", "tắt", "tat", "off", "on"]):
        return "device"
    if is_comfort_request(t):
        return "comfort_request"
    return "help"


def detect_profile_from_text(text: str) -> str:
    t = normalize_text(text)
    if any(x in t for x in ["eco", "tiết kiệm", "tiet kiem"]):
        return "eco"
    if any(x in t for x in ["sleep", "ngủ", "ngu", "đi ngủ", "di ngu"]):
        return "sleep"
    if any(x in t for x in ["movie", "phim", "xem phim"]):
        return "movie"
    if any(x in t for x in ["away", "vắng", "vang", "ra ngoài", "ra ngoai"]):
        return "away"
    if any(x in t for x in ["guest", "khách", "khach"]):
        return "guest"
    return "comfort"


def detect_device_from_text(text: str) -> str | None:
    t = normalize_text(text)
    # Prefer longer aliases first so "hút mùi" beats generic words.
    for alias, device_id in sorted(DEVICE_ALIAS.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in t:
            return device_id
    if "lọc" in t or "bụi" in t or "pm" in t:
        return "purifier"
    if "mùi" in t or "gas" in t:
        return "hood"
    return None


def numbers_in_text(text: str) -> list[float]:
    out: list[float] = []
    for match in re.findall(r"\d+(?:[\.,]\d+)?", text or ""):
        try:
            out.append(float(match.replace(",", ".")))
        except Exception:
            pass
    return out


def infer_patch_for_device(text: str, device_id: str) -> dict[str, Any]:
    t = normalize_text(text)
    nums = numbers_in_text(t)
    last_number = nums[-1] if nums else -1
    patch: dict[str, Any] = {}

    if device_id in {"fan", "light", "hood"}:
        power = extract_number_after_keywords(
            t,
            ["công suất", "cong suat", "power", "%", "quạt", "quat", "đèn", "den", "hút mùi", "hut mui"],
            -1,
        )
        if power < 0 and 10 <= last_number <= 100:
            power = last_number
        if power < 0:
            # If the message contains "mạnh/nhẹ", infer a practical value.
            if any(x in t for x in ["mạnh", "manh", "cao", "nhanh"]):
                power = 75
            elif any(x in t for x in ["nhẹ", "nhe", "thấp", "thap"]):
                power = 25
        if power >= 0:
            patch["power"] = int(max(10, min(100, power)))

    if device_id == "ac":
        target = extract_number_after_keywords(
            t,
            ["target", "máy lạnh", "may lanh", "điều hòa", "dieu hoa", "nhiệt độ", "nhiet do"],
            -1,
        )
        if target < 0 and 18 <= last_number <= 30:
            target = last_number
        if target >= 0:
            patch["target"] = int(max(18, min(30, target)))
        elif any(x in t for x in ["mát", "mat", "lạnh", "lanh"]):
            patch["target"] = 25
    return patch


def summarize_status(state: dict[str, Any], room_id: str | None = None) -> str:
    rooms = state.get("rooms", {})
    target_rooms = {room_id: rooms[room_id]} if room_id and room_id in rooms else rooms
    parts: list[str] = []
    for rid, room in target_rooms.items():
        s = room.get("sensors", {})
        active = [d.get("name", did) for did, d in room.get("devices", {}).items() if d.get("on")]
        parts.append(
            f"{room.get('name', rid)}: {s.get('temperature', '--')}°C, "
            f"ẩm {s.get('humidity', '--')}%, PM2.5 {s.get('pm25', '--')}; "
            f"đang bật: {', '.join(active) if active else 'không có'}"
        )
    return "Tình trạng hiện tại:\n- " + "\n- ".join(parts)



def is_comfort_request(text: str) -> bool:
    t = normalize_text(text)
    comfort_words = [
        "hơi nóng", "hoi nong", "nóng", "nong", "ngột", "ngot", "bí", "bi", "khó chịu", "kho chiu",
        "hơi lạnh", "hoi lanh", "lạnh", "lanh", "ẩm", "am", "khô", "kho", "bụi", "bui", "ngột ngạt", "ngot ngat"
    ]
    return any(w in t for w in comfort_words)


def record_comfort_feedback(state: dict[str, Any], room_id: str, text: str) -> dict[str, Any]:
    t = normalize_text(text)
    room = state.get("rooms", {}).get(room_id, {})
    sensors = room.get("sensors", {})
    temp = _to_float(sensors.get("temperature"), 28)
    hum = _to_float(sensors.get("humidity"), 60)
    prof = state.setdefault("learning_profile", {}).setdefault(room_id, {})
    prof["feedback_count"] = int(prof.get("feedback_count", 0)) + 1
    prof["last_feedback"] = text[:160]
    prof["last_feedback_at"] = now_iso()

    if any(x in t for x in ["nóng", "nong", "ngột", "ngot", "bí", "bi", "khó chịu", "kho chiu"]):
        # If user feels hot at this temperature, start cooling slightly earlier next time.
        prof["fan_on_at"] = round(min(float(prof.get("fan_on_at", 28.0)), max(26.0, temp - 0.4)), 1)
        prof["ac_on_at"] = round(min(float(prof.get("ac_on_at", 32.0)), max(30.0, temp + 1.0)), 1)
        prof["ac_target"] = int(min(int(prof.get("ac_target", 26)), 26))
    if any(x in t for x in ["lạnh", "lanh", "rét", "ret"]):
        prof["fan_on_at"] = round(max(float(prof.get("fan_on_at", 28.0)), min(30.0, temp + 0.8)), 1)
        prof["ac_on_at"] = round(max(float(prof.get("ac_on_at", 32.0)), min(33.5, temp + 2.0)), 1)
        prof["ac_target"] = int(max(int(prof.get("ac_target", 26)), 27))
    if any(x in t for x in ["ẩm", "am", "nồm", "nom"]):
        prof["humidity_high_at"] = round(min(float(prof.get("humidity_high_at", 78.0)), max(65.0, hum - 2)), 1)
    return prof


def apply_room_adaptive_comfort(state: dict[str, Any], room_id: str, text: str) -> list[str]:
    room = state.get("rooms", {}).get(room_id)
    if not room:
        return []
    prof = record_comfort_feedback(state, room_id, text)
    s = room.get("sensors", {})
    d = room.get("devices", {})
    temp = _to_float(s.get("temperature"), 28)
    hum = _to_float(s.get("humidity"), 60)
    pm = _to_float(s.get("pm25"), 0)
    felt = temp + max(0, hum - 65) * 0.045 + max(0, pm - 35) * 0.018
    fan_on_at = float(prof.get("fan_on_at", 28.0))
    ac_on_at = float(prof.get("ac_on_at", 32.0))
    ac_target = int(prof.get("ac_target", 26))
    plan: list[str] = []

    def turn(device_id: str, on: bool, patch: dict[str, Any] | None = None, reason: str = "") -> None:
        dev = d.get(device_id)
        if not dev:
            return
        before = json.dumps({k: dev.get(k) for k in ["on", "power", "target", "mode"]}, sort_keys=True, ensure_ascii=False)
        dev["on"] = bool(on)
        if patch:
            for k, v in patch.items():
                if v is not None:
                    dev[k] = v
        after = json.dumps({k: dev.get(k) for k in ["on", "power", "target", "mode"]}, sort_keys=True, ensure_ascii=False)
        if before != after:
            set_manual_override(state, room_id, device_id, reason="adaptive-chat", ttl_minutes=75)
            plan.append(_device_summary(room, device_id, dev, reason))

    t = normalize_text(text)
    if any(x in t for x in ["lạnh", "lanh", "rét", "ret"]):
        turn("fan", False, reason="bạn báo hơi lạnh")
        turn("ac", False, reason="bạn báo hơi lạnh")
        if hum >= float(prof.get("humidity_high_at", 78.0)):
            turn("dehumidifier", True, reason=f"vẫn giữ hút ẩm vì độ ẩm {hum:g}%")
    elif any(x in t for x in ["ẩm", "am", "nồm", "nom"]):
        threshold = float(prof.get("humidity_high_at", 76.0))
        if hum >= threshold:
            turn("dehumidifier", True, reason=f"bạn báo ẩm, độ ẩm hiện {hum:g}%")
        if felt >= fan_on_at:
            power = int(max(28, min(58, 34 + (felt - fan_on_at) * 8)))
            turn("fan", True, {"power": power}, "tăng lưu thông khí để bớt bí")
    else:
        # Hot / stuffy / general comfort complaint.
        if felt >= ac_on_at and "ac" in d:
            target = ac_target if felt < ac_on_at + 1.5 else max(24, ac_target - 1)
            boost = min(12, max(0, int(prof.get("feedback_count", 1)) - 1) * 6)
            fan_power = int(max(32, min(70, 36 + (felt - ac_on_at) * 8 + boost)))
            turn("ac", True, {"target": target}, f"bạn thấy nóng, cảm giác khoảng {felt:.1f}°C")
            turn("fan", True, {"power": fan_power}, "hỗ trợ máy lạnh để tiết kiệm điện")
        elif felt >= fan_on_at and "fan" in d:
            boost = min(18, max(0, int(prof.get("feedback_count", 1)) - 1) * 6)
            power = int(max(36, min(80, 42 + (felt - fan_on_at) * 9 + boost)))
            turn("fan", True, {"power": power}, f"bạn thấy hơi nóng, dùng quạt trước cho tiết kiệm")
            if "ac" in d:
                turn("ac", False, reason="chưa cần máy lạnh nếu quạt đủ dễ chịu")
        elif temp < 25:
            turn("fan", False, reason="nhiệt độ đang thấp")
            turn("ac", False, reason="nhiệt độ đang thấp")
        else:
            # Even if still in comfort range, a small airflow often feels better.
            if "fan" in d:
                turn("fan", True, {"power": 32}, "tạo gió nhẹ vì bạn thấy chưa thoải mái")
    if pm >= 38 and "purifier" in d:
        turn("purifier", True, reason=f"PM2.5 {pm:g}, không khí có thể làm bạn thấy bí")
    if hum >= 78 and "dehumidifier" in d:
        turn("dehumidifier", True, reason=f"độ ẩm cao {hum:g}%")
    state["last_comfort_plan"] = {
        "profile": "adaptive-chat",
        "items": plan or [f"{room.get('name', room_id)} đang khá ổn; mình chỉ ghi nhận sở thích để lần sau tối ưu sớm hơn."],
        "summary": f"Smart Chat đã tối ưu {room.get('name', room_id)} theo phản hồi thật của bạn.",
        "updated_at": now_iso(),
    }
    add_event(state, "Smart Chat tự học comfort", f"{room.get('name', room_id)}: {text[:120]}", "ai")
    save_state(state)
    return plan

def process_smart_bubble_message(message: str) -> dict[str, Any]:
    text = str(message or "").strip()
    if not text:
        raise ValueError("Bạn chưa nhập nội dung")
    intent = detect_intent_from_text(text)
    t = normalize_text(text)

    if intent == "note":
        result = create_smart_note_from_text(text)
        result["intent"] = "note"
        return result

    if intent == "auto":
        profile = detect_profile_from_text(text)
        state = load_state()
        clear_manual_overrides(state)
        save_state(state)
        state = run_homeos_tick(profile)
        plan = state.get("last_comfort_plan") or {}
        items = plan.get("items") or []
        reply = f"Mình đã chạy {profile} mode và tối ưu toàn nhà."
        if items:
            reply += "\n- " + "\n- ".join(items[:8])
        else:
            reply += " Nhà đang khá ổn nên chưa cần đổi nhiều."
        return {"state": state, "note": None, "reply": reply, "created_rules": [], "intent": "auto"}

    if intent == "device":
        room_id = infer_room_from_text(text)
        device_id = detect_device_from_text(text)
        if not device_id:
            raise ValueError("Mình chưa nhận ra thiết bị cần điều khiển. Ví dụ: bật quạt phòng ngủ, tắt đèn phòng khách.")
        on = not any(x in t for x in ["tắt", "tat", "off", "đóng", "dong"])
        patch = infer_patch_for_device(text, device_id)
        state = set_device(room_id, device_id, on=on, patch=patch, source="chat", override_minutes=90)
        room = state["rooms"][room_id]
        device = room["devices"][device_id]
        extras = []
        if "power" in device:
            extras.append(f"{device.get('power')}%")
        if "target" in device:
            extras.append(f"{device.get('target')}°C")
        suffix = f" ({', '.join(extras)})" if extras else ""
        reply = f"Đã {'bật' if on else 'tắt'} {device.get('name', device_id)} ở {room.get('name', room_id)}{suffix}."
        return {"state": state, "note": None, "reply": reply, "created_rules": [], "intent": "device"}

    if intent == "comfort_request":
        state = load_state()
        room_id = infer_room_from_text(text)
        plan = apply_room_adaptive_comfort(state, room_id, text)
        room = state.get("rooms", {}).get(room_id, {})
        s = room.get("sensors", {})
        reply = (
            f"Mình hiểu là {room.get('name', room_id)} đang chưa thoải mái. "
            f"Hiện khoảng {s.get('temperature', '--')}°C, độ ẩm {s.get('humidity', '--')}%, PM2.5 {s.get('pm25', '--')}. "
        )
        if plan:
            reply += "Mình đã tự điều chỉnh theo hướng dễ chịu trước nhưng vẫn tiết kiệm điện:\n- " + "\n- ".join(plan[:6])
        else:
            active = []
            for did, dev in room.get("devices", {}).items():
                if dev.get("on"):
                    extra = []
                    if "power" in dev:
                        extra.append(f"{dev.get('power')}%")
                    if "target" in dev:
                        extra.append(f"{dev.get('target')}°C")
                    suffix = f" ({', '.join(extra)})" if extra else ""
                    active.append(f"{dev.get('name', did)}{suffix}")
            if active:
                reply += "Mình giữ các thiết bị đang phù hợp: " + ", ".join(active[:4]) + ". Mình cũng ghi nhận phản hồi này để lần sau làm mát sớm hơn."
            else:
                reply += "Mình đã ghi nhận cảm giác của bạn để lần sau tự làm mát sớm hơn."
        return {"state": state, "note": None, "reply": reply, "created_rules": [], "intent": "comfort_request"}

    state = load_state()
    if intent == "status":
        room_id = infer_room_from_text(text) if any(alias in t for alias in ROOM_ALIAS) else None
        reply = summarize_status(state, room_id)
        return {"state": state, "note": None, "reply": reply, "created_rules": [], "intent": "status"}

    if intent == "energy":
        report = compute_energy_optimization(state)
        tips = report.get("tips", [])
        reply = (
            f"Điện hiện tại khoảng {report.get('total_w', 0)}W, "
            f"ước tính {report.get('estimated_kwh_day', 0)} kWh/ngày, "
            f"~{report.get('estimated_cost_day_vnd', 0):,}đ/ngày."
        )
        if tips:
            reply += "\n- " + "\n- ".join(tips[:5])
        return {"state": state, "note": None, "reply": reply, "created_rules": [], "intent": "energy"}

    if intent == "alerts":
        alerts = generate_alerts(state)
        if not alerts:
            reply = "Hiện chưa có cảnh báo lớn. Nhà đang khá ổn."
        else:
            reply = "Các cảnh báo đang có:\n- " + "\n- ".join(f"{a.get('title')}: {a.get('detail')}" for a in alerts[:8])
        return {"state": state, "note": None, "reply": reply, "created_rules": [], "intent": "alerts"}

    reply = (
        "Mình có thể làm các việc sau:\n"
        "- Tạo/sửa note thông minh, ví dụ: tạo note phòng ngủ nóng thì ưu tiên làm mát.\n"
        "- Điều khiển thiết bị, ví dụ: bật quạt phòng ngủ 55%.\n"
        "- Chạy auto mode, ví dụ: tối ưu nhà theo eco hoặc bật movie mode.\n"
        "- Hỏi tình trạng, điện năng hoặc cảnh báo."
    )
    return {"state": state, "note": None, "reply": reply, "created_rules": [], "intent": "help"}


def enrich(state: dict[str, Any]) -> dict[str, Any]:
    alerts = generate_alerts(state)
    state["alerts"] = alerts
    return {
        "state": state,
        "home_score": compute_home_score(state),
        "energy": estimate_energy(state),
        "energy_report": compute_energy_optimization(state),
        "alerts": alerts,
        "rules": state.get("user_rules", []),
        "smart_notes": state.get("smart_notes", []),
        "learning_profile": state.get("learning_profile", {}),
        "scenes": SCENES,
        "suggestions": build_quick_suggestions(state),
    }
