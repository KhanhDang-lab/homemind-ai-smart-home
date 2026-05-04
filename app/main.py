from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .ollama_ai import DEFAULT_MODEL, OllamaError, analyze_home_with_ollama, call_ollama, command_with_ollama, parse_json, smart_chat_reply_with_ollama
from .state import (
    apply_actions,
    apply_comfort_auto,
    apply_scene,
    compute_energy_optimization,
    create_smart_note_from_text,
    process_smart_bubble_message,
    delete_smart_note,
    delete_user_rule,
    generate_alerts,
    build_quick_suggestions,
    enrich,
    load_history,
    load_state,
    reset_state,
    save_state,
    set_device,
    simulate_sensors,
    snapshot_for_ai,
    toggle_automation,
    toggle_smart_note,
    toggle_user_rule,
    update_sensors,
    upsert_user_rule,
    run_homeos_tick,
    local_command_actions,
    add_event,
    apply_firebase_sync,
)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="HomeMind Demo Optimized v28", version="4.5.0")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def ok(state: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    if state is None:
        state = load_state()
    return {"ok": True, **enrich(state), **extra}


def fail(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"ok": False, "error": message})


@app.exception_handler(ValueError)
def value_error_handler(_: Request, exc: ValueError):
    return fail(str(exc), 400)


@app.exception_handler(OllamaError)
def ollama_error_handler(_: Request, exc: OllamaError):
    return fail(str(exc), 503)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"title": "HomeMind Demo Optimized v28"})


@app.get("/api/health")
def api_health():
    state = load_state()
    return ok(state, app="HomeMind Demo Optimized v28", default_model=DEFAULT_MODEL)


@app.get("/api/state")
def api_state():
    return ok(load_state())




@app.get("/api/climate")
def api_climate():
    state = load_state()
    rooms = state.get("rooms", {})
    climate = []
    for room_id, room in rooms.items():
        sensors = room.get("sensors", {})
        climate.append({
            "room_id": room_id,
            "name": room.get("name", room_id),
            "icon": room.get("icon", "🏠"),
            "temperature": sensors.get("temperature"),
            "humidity": sensors.get("humidity"),
            "updated_at": state.get("updated_at"),
        })
    return {"ok": True, "updated_at": state.get("updated_at"), "climate": climate}


@app.post("/api/firebase/sync")
def api_firebase_sync(payload: dict = Body(...)):
    state = apply_firebase_sync(payload)
    return ok(state, message="Đã đồng bộ Firebase vào dashboard")


@app.post("/api/simulate")
def api_simulate():
    return ok(simulate_sensors())


@app.post("/api/reset")
def api_reset():
    return ok(reset_state())


@app.get("/api/history")
def api_history(limit: int = 90):
    return {"ok": True, "history": load_history(limit=limit)}


@app.get("/api/suggestions")
def api_suggestions():
    state = load_state()
    return {"ok": True, "suggestions": build_quick_suggestions(state)}


@app.get("/api/energy")
def api_energy():
    state = load_state()
    return {"ok": True, "energy_report": compute_energy_optimization(state), "energy": ok(state)["energy"]}


@app.get("/api/alerts")
def api_alerts():
    state = load_state()
    return {"ok": True, "alerts": generate_alerts(state)}


@app.get("/api/rules")
def api_rules():
    state = load_state()
    return {"ok": True, "rules": state.get("user_rules", [])}


@app.post("/api/rules")
def api_rule_create(payload: dict = Body(...)):
    state = upsert_user_rule(payload)
    return ok(state, message="Đã lưu rule")


@app.post("/api/rules/toggle")
def api_rule_toggle(payload: dict = Body(...)):
    state = toggle_user_rule(str(payload.get("id")), bool(payload.get("enabled")))
    return ok(state, message="Đã cập nhật rule")


@app.delete("/api/rules/{rule_id}")
def api_rule_delete(rule_id: str):
    state = delete_user_rule(rule_id)
    return ok(state, message="Đã xóa rule")


@app.post("/api/homeos/tick")
def api_homeos_tick(payload: dict = Body(default_factory=dict)):
    state = run_homeos_tick(payload.get("profile") or "comfort")
    return ok(state, message="HomeOS Tick đã tối ưu nhà")


@app.get("/api/smart-notes")
def api_smart_notes():
    state = load_state()
    return {"ok": True, "smart_notes": state.get("smart_notes", [])}


@app.post("/api/smart-bubble")
def api_smart_bubble(payload: dict = Body(...)):
    message = str(payload.get("message") or "")
    model = payload.get("model") or DEFAULT_MODEL
    result = process_smart_bubble_message(message)
    used_ollama = False
    ai_error = None
    try:
        ai_reply = smart_chat_reply_with_ollama(snapshot_for_ai(result["state"]), message, result, model=model)
        # Ollama is used to make the language warmer, but for device/note/auto actions
        # the deterministic backend reply stays the source of truth to avoid saying
        # "already ON" while another flow changed the state.
        if result.get("intent") in {"status", "energy", "alerts", "help"} and ai_reply.get("reply"):
            result["reply"] = ai_reply["reply"]
        result["ai_reply"] = ai_reply
        used_ollama = True
    except Exception as exc:
        ai_error = str(exc)
    return ok(
        result["state"],
        note=result.get("note"),
        reply=result.get("reply"),
        created_rules=result.get("created_rules", []),
        intent=result.get("intent"),
        used_ollama=used_ollama,
        ai_error=ai_error,
    )


@app.post("/api/smart-notes/toggle")
def api_smart_note_toggle(payload: dict = Body(...)):
    state = toggle_smart_note(str(payload.get("id")), bool(payload.get("enabled")))
    return ok(state, message="Đã cập nhật smart note")


@app.delete("/api/smart-notes/{note_id}")
def api_smart_note_delete(note_id: str):
    state = delete_smart_note(note_id)
    return ok(state, message="Đã xóa smart note")



@app.post("/api/device")
def api_device(payload: dict = Body(...)):
    room_id = payload.get("room_id")
    device_id = payload.get("device_id")
    state = set_device(room_id, device_id, on=payload.get("on"), patch=payload.get("patch") or {}, source="manual", override_minutes=90)
    return ok(state)


@app.post("/api/scene")
def api_scene(payload: dict = Body(...)):
    state = apply_scene(payload.get("scene"))
    return ok(state)


@app.post("/api/auto/comfort")
def api_auto_comfort(payload: dict = Body(default_factory=dict)):
    state = apply_comfort_auto(payload.get("profile") or "comfort")
    return ok(state, plan=state.get("last_comfort_plan"), message="Comfort Auto đã tối ưu nhà")


@app.post("/api/automation/toggle")
def api_automation_toggle(payload: dict = Body(...)):
    state = toggle_automation(payload.get("id"), bool(payload.get("enabled")))
    return ok(state)


@app.post("/api/telemetry")
def api_telemetry(payload: dict = Body(...)):
    state = update_sensors(payload.get("room_id"), payload.get("sensors", {}))
    return ok(state, message="Đã nhận telemetry")


@app.get("/api/test-ollama")
def api_test_ollama(model: str = DEFAULT_MODEL):
    raw = call_ollama(
        'Trả về đúng JSON: {"ok": true, "message": "Ollama connected", "model_note": "AI local đã sẵn sàng"}',
        model=model,
        timeout=60,
        temperature=0.1,
        num_predict=180,
    )
    parsed = parse_json(raw)
    return {"ok": True, "model": model, "raw": raw, "parsed": parsed}


@app.post("/api/ai/analyze")
def api_ai_analyze(payload: dict = Body(default_factory=dict)):
    model = payload.get("model") or DEFAULT_MODEL
    state = load_state()
    advice = analyze_home_with_ollama(snapshot_for_ai(state), model=model)
    state["last_ai"] = {"type": "analyze", "model": model, "advice": advice}
    add_event(state, "AI phân tích nhà", f"Model: {model}", "ai")
    save_state(state)
    return ok(state, advice=advice)


@app.post("/api/ai/command")
def api_ai_command(payload: dict = Body(...)):
    model = payload.get("model") or DEFAULT_MODEL
    command = str(payload.get("command") or "").strip()
    auto_apply = payload.get("auto_apply", True)
    if not command:
        raise HTTPException(status_code=400, detail="Bạn chưa nhập lệnh")

    state_before = load_state()
    used_fallback = False
    try:
        ai = command_with_ollama(snapshot_for_ai(state_before), command, model=model)
    except Exception as exc:
        actions, local_message = local_command_actions(command)
        ai = {
            "understanding": local_message,
            "intent": "fallback",
            "response": f"Ollama đang lỗi nên mình dùng parser local tạm thời. Lỗi: {exc}",
            "actions": actions,
            "suggested_actions": [],
            "automation_idea": {},
            "model": "local-fallback",
        }
        used_fallback = True

    applied: list[str] = []
    state_after = state_before
    if auto_apply and ai.get("actions"):
        state_after, applied = apply_actions(ai.get("actions", []), source="ai-fallback" if used_fallback else "ai")
    else:
        add_event(state_after, "AI command", command, "ai")
        save_state(state_after)

    state_after["last_ai"] = {"type": "command", "command": command, "model": model, "ai": ai, "applied": applied}
    save_state(state_after)
    return ok(state_after, ai=ai, applied=applied, used_fallback=used_fallback)
