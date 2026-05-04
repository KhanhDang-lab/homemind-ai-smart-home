# System Architecture

HomeMind AI Smart Home Dashboard is designed as an end-to-end Embedded IoT system that connects sensor data, realtime database synchronization, backend processing, dashboard control, and AI-assisted automation.

---

## Overall Workflow

```txt
ESP32 / Sensors
      ↓
Firebase Realtime Database
      ↓
FastAPI Backend
      ↓
Web Dashboard
      ↓
AI-assisted Automation
