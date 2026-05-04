from __future__ import annotations

from typing import Any
import json
import urllib.error
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:7b"


class OllamaError(RuntimeError):
    pass


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 120, *, temperature: float = 0.55, num_predict: int = 1800) -> str:
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_ctx": 8192,
            "num_predict": num_predict,
        },
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw).get("response", "")
    except urllib.error.URLError as exc:
        raise OllamaError(f"Không kết nối được Ollama tại {OLLAMA_URL}. Hãy chạy: ollama serve. Chi tiết: {exc}") from exc
    except Exception as exc:
        raise OllamaError(f"Ollama lỗi: {exc}") from exc


def parse_json(text: str) -> dict[str, Any]:
    if not text:
        raise ValueError("Ollama trả về rỗng")
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Ollama không trả JSON hợp lệ")
        return json.loads(text[start:end + 1])


def analyze_home_with_ollama(snapshot: dict[str, Any], model: str) -> dict[str, Any]:
    prompt = f"""
Bạn là AI điều phối Smart Home chạy local bằng Ollama. Hãy phân tích trạng thái nhà thông minh bằng tiếng Việt tự nhiên, có chiều sâu, nhưng bắt buộc trả về đúng JSON, không markdown, không giải thích ngoài JSON.

Dữ liệu nhà:
{json.dumps(snapshot, ensure_ascii=False, indent=2)}

Schema JSON bắt buộc:
{{
  "home_summary": "5-8 câu tóm tắt nhà hiện tại, tự nhiên, có ngữ cảnh.",
  "priority": "LOW | MEDIUM | HIGH",
  "top_insights": ["4-7 nhận định sâu, không lặp ý"],
  "room_advice": [
    {{"room": "Tên phòng", "status": "ổn | cần chú ý | ưu tiên xử lý", "reason": "vì sao", "actions": ["3-5 hành động cụ thể"]}}
  ],
  "energy_advice": "3-5 câu về tiết kiệm điện dựa trên thiết bị đang bật.",
  "security_advice": "3-5 câu về cửa/chuyển động/camera.",
  "automation_ideas": [
    {{"title": "Tên automation", "trigger": "điều kiện", "action": "hành động", "why": "vì sao hữu ích"}}
  ],
  "quick_actions": ["5-8 hành động nhanh"],
  "takeaway": "Một câu chốt tự nhiên"
}}
""".strip()
    data = parse_json(call_ollama(prompt, model=model, timeout=150, temperature=0.68, num_predict=2600))
    data.setdefault("home_summary", "")
    data.setdefault("priority", "MEDIUM")
    data.setdefault("top_insights", [])
    data.setdefault("room_advice", [])
    data.setdefault("energy_advice", "")
    data.setdefault("security_advice", "")
    data.setdefault("automation_ideas", [])
    data.setdefault("quick_actions", [])
    data.setdefault("takeaway", "")
    data["model"] = model
    return data


def command_with_ollama(snapshot: dict[str, Any], command: str, model: str) -> dict[str, Any]:
    prompt = f"""
Bạn là AI trợ lý điều khiển Smart Home. Nhiệm vụ: hiểu lệnh tiếng Việt tự nhiên, trả lời thân thiện, và nếu có thể thì tạo danh sách action JSON để backend áp dụng.

Quan trọng:
- Chỉ dùng room_id có trong dữ liệu: living_room, bedroom, kitchen, garden.
- Chỉ dùng device_id có trong từng phòng.
- Mapping quan trọng: hút mùi nhà bếp = room_id "kitchen", device_id "hood". Không dùng "hut_mui" trong actions.
- Nếu người dùng muốn bật/tắt thiết bị, tạo action type=device.
- Nếu người dùng muốn scene, tạo action type=scene với scene: sleep, away, focus, movie, clean_air, garden.
- Nếu chỉ hỏi thông tin, actions để mảng rỗng.
- Không bịa thiết bị không tồn tại.
- Trả về đúng JSON, không markdown.

Lệnh người dùng: {command}

Trạng thái nhà:
{json.dumps(snapshot, ensure_ascii=False, indent=2)}

Schema JSON bắt buộc:
{{
  "understanding": "Bạn hiểu lệnh này là gì",
  "intent": "control | scene | question | automation | unknown",
  "response": "Phản hồi tự nhiên cho người dùng, có thể nói đã/ sẽ thực hiện gì",
  "actions": [
    {{"type": "device", "room_id": "living_room", "device_id": "light", "on": true, "patch": {{}}}},
    {{"type": "scene", "scene": "sleep"}}
  ],
  "suggested_actions": ["các hành động nên làm tiếp theo"],
  "automation_idea": {{"title": "nếu phù hợp", "trigger": "nếu phù hợp", "action": "nếu phù hợp"}}
}}
""".strip()
    data = parse_json(call_ollama(prompt, model=model, timeout=120, temperature=0.38, num_predict=1700))
    data.setdefault("understanding", "")
    data.setdefault("intent", "unknown")
    data.setdefault("response", "")
    data.setdefault("actions", [])
    data.setdefault("suggested_actions", [])
    data.setdefault("automation_idea", {})
    data["model"] = model
    return data


def smart_chat_reply_with_ollama(snapshot: dict[str, Any], user_message: str, local_result: dict[str, Any], model: str) -> dict[str, Any]:
    """Use local Ollama to make the Smart Chat answer feel natural.

    The backend already applied safe deterministic actions. Ollama is used for
    language and explanation, not for unsafe direct hardware changes.
    """
    prompt = f"""
Bạn là AI Smart Home local chạy bằng Ollama. Hãy trả lời người dùng bằng tiếng Việt tự nhiên, mềm mại, giống trợ lý nhà thông minh thật.

Nguyên tắc:
- Không trả lời cứng nhắc kiểu template.
- Nói rõ bạn đã làm gì và vì sao: thoải mái + tiết kiệm điện.
- Nếu hệ thống đã bật quạt trước thay vì máy lạnh, giải thích là để tiết kiệm điện nhưng vẫn dễ chịu.
- Nếu đã bật máy lạnh, nói target hợp lý và quạt hỗ trợ nếu có.
- Không bịa hành động chưa có trong local_result.
- Trả về đúng JSON, không markdown.

Tin nhắn người dùng:
{user_message}

Kết quả backend đã xử lý:
{json.dumps(local_result, ensure_ascii=False, indent=2)}

Snapshot nhà hiện tại:
{json.dumps(snapshot, ensure_ascii=False, indent=2)}

Schema JSON:
{{
  "reply": "phản hồi tự nhiên 3-7 câu, có cảm giác đang hiểu hoàn cảnh người dùng",
  "tone": "calm | proactive | warning",
  "short_label": "nhãn rất ngắn cho UI"
}}
""".strip()
    data = parse_json(call_ollama(prompt, model=model, timeout=90, temperature=0.72, num_predict=900))
    data.setdefault("reply", local_result.get("reply", "Mình đã xử lý xong."))
    data.setdefault("tone", "proactive")
    data.setdefault("short_label", "Smart Chat")
    data["model"] = model
    return data
