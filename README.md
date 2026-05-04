---

## Key Features

- Realtime monitoring for temperature, humidity, PM2.5 and room status
- Smart device control through Firebase Realtime Database
- Web dashboard for monitoring and controlling smart devices
- Automation logic based on sensor conditions
- AI Smart Chat for natural language interaction
- Smart Notes automation system for rule-based control
- Alert-based UI reactions for abnormal environmental conditions
- Dark / Light mode dashboard
- Energy usage estimation and optimization suggestions

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Embedded / IoT** | ESP32, Arduino, C/C++, Sensors, Relay Module |
| **Realtime Database** | Firebase Realtime Database |
| **Backend** | Python, FastAPI, REST API |
| **Frontend** | HTML, CSS, JavaScript |
| **AI-assisted Features** | Local AI / Ollama, Smart Notes, Natural Language Commands |

---

## Demo Video

<div align="center">

[![Watch Demo Video](https://img.shields.io/badge/Watch%20Demo-HomeMind%20AI%20Smart%20Home-2563EB?style=for-the-badge&logo=googledrive&logoColor=white)](https://drive.google.com/file/d/1gaampTVrBAsVZE6X8f8OjjAExAJHJfi5/view?usp=sharing)

</div>

This demo video presents the main workflow of the **HomeMind AI Smart Home Dashboard**, including realtime data synchronization, dashboard monitoring, device control, automation modes, AI Assistant interaction, and Smart Notes automation.

### Demo Highlights

| Feature | Description |
|---|---|
| **Firebase Realtime Sync** | Sensor data and device states are synchronized through Firebase Realtime Database |
| **Dashboard Monitoring** | Realtime room status, power usage, alerts and system mode are displayed on the dashboard |
| **Smart Device Control** | Devices can be controlled directly from the web interface |
| **Auto Mode Automation** | Comfort, Eco, Sleep and Focus modes adjust the system based on usage scenarios |
| **AI Assistant** | Users can interact with the system using natural language commands |
| **Smart Notes** | Automation rules can be created from simple user requests |

---

## Demo Screenshots

### Dashboard Overview

| Main Dashboard | Automation Mode |
|---|---|
| ![Dashboard Overview](./screenshots/dashboard/1.png) | ![Automation Mode](./screenshots/dashboard/2.png) |

| Room Control | Alert & AI Summary |
|---|---|
| ![Room Control](./screenshots/dashboard/3.png) | ![Alert and AI Summary](./screenshots/dashboard/4.png) |

### AI Assistant

![AI Chat Preview](./screenshots/ai-chat/5.png)

### Firebase Realtime Database Sync

![Firebase Sync Preview](./screenshots/firebase-sync/6.png)

---

---

## How to Run

Follow the steps below to run the project locally.

---

### 1. Clone the repository

```bash
git clone https://github.com/KhanhDang-lab/homemind-ai-smart-home.git
cd homemind-ai-smart-home
```

---

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate the virtual environment.

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Firebase Setup

This project uses **Firebase Realtime Database** to store realtime sensor data and device commands.

---

### 4. Create a Firebase project

1. Go to Firebase Console: `https://console.firebase.google.com/`
2. Click **Add project**
3. Enter a project name
4. Continue until the project is created

---

### 5. Create Realtime Database

1. Open your Firebase project
2. Go to **Build**
3. Select **Realtime Database**
4. Click **Create Database**
5. Choose a database location
6. For demo/testing, choose **Start in test mode**

After creating the database, copy your Realtime Database URL.

Example:

```txt
https://your-project-id-default-rtdb.firebaseio.com
```

---

### 6. Register a Firebase Web App

1. Go to **Project settings**
2. Scroll down to **Your apps**
3. Click the Web icon `</>`
4. Register a web app
5. Copy the Firebase config object

Example config:

```js
const firebaseConfig = {
  apiKey: "YOUR_FIREBASE_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  databaseURL: "https://YOUR_PROJECT-default-rtdb.firebaseio.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.firebasestorage.app",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID",
  measurementId: "YOUR_MEASUREMENT_ID"
};
```

---

### 7. Create Firebase config file

Create this file locally:

```txt
app/static/firebase_config.js
```

Paste your Firebase config into `firebase_config.js`.

Example:

```js
const firebaseConfig = {
  apiKey: "YOUR_FIREBASE_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  databaseURL: "https://YOUR_PROJECT-default-rtdb.firebaseio.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.firebasestorage.app",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID",
  measurementId: "YOUR_MEASUREMENT_ID"
};
```

Important:

```txt
Do not upload app/static/firebase_config.js to GitHub.
```

This repository only includes the example file:

```txt
app/static/firebase_config.example.js
```

---

### 8. Import Firebase demo data

This project provides sample demo data for Firebase Realtime Database.

Demo JSON file:

```txt
firebase/smart-home-demo-data.json
```

To import the demo data:

1. Open Firebase Console
2. Go to **Realtime Database**
3. Open the **Data** tab
4. Click the three-dot menu
5. Select **Import JSON**
6. Choose:

```txt
firebase/smart-home-demo-data.json
```

After importing, your database should contain:

```txt
smart-home
├── commands
├── value
├── history
└── notes
```

The dashboard reads sensor data from:

```txt
smart-home/value
```

The dashboard writes device commands to:

```txt
smart-home/commands
```

---

## Run the Application

### 9. Start the backend server

```bash
python run_app.py
```

Then open the dashboard:

```txt
http://127.0.0.1:8000
```

---

## Optional: Run Local AI with Ollama

This project can work with local AI through Ollama.

### 10. Install Ollama

Download and install Ollama from:

```txt
https://ollama.com
```

### 11. Pull a local model

Example:

```bash
ollama pull qwen2.5:7b
```

### 12. Run Ollama

```bash
ollama serve
```

If Ollama is already running in the background, you do not need to run this command again.

The default local AI model can be configured in:

```txt
.env.example
```

Example:

```env
OLLAMA_MODEL=qwen2.5:7b
```

---

## Common Issues

### Firebase does not sync

Check these items:

- `app/static/firebase_config.js` exists
- `databaseURL` is correct
- Realtime Database has the `smart-home` root node
- Firebase rules allow read/write for demo testing

For demo only, test rules may look like this:

```json
{
  "rules": {
    ".read": true,
    ".write": true
  }
}
```

Do not use public read/write rules in production.

---

### Module not found

If Python reports missing packages, run:

```bash
pip install -r requirements.txt
```

---

### Port already in use

If port `8000` is already used, stop the previous server or run the app on another port if supported.

---

## Notes

- This project is a demo/prototype for Embedded IoT and Smart Home automation.
- Real Firebase credentials are not included in this repository.
- Local Firebase configuration should be created manually.
- The demo JSON file is provided so users can quickly test the dashboard.
