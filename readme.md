# 🧠 BCI Backend

This repository contains the backend service for a Brain-Computer Interface (BCI) system that processes EEG signals and controls a virtual interface based on user brain activity.

---

## 📌 Project Overview

- **Goal**: Receive EEG signals, classify them using ML models, and expose the results to the frontend via APIs.
- **Framework**: Built using **FastAPI** for lightweight, high-performance RESTful services.
- **Functionality**: Handles authentication, EEG signal processing, prediction, and session tracking.

---

## ✨ Features

- User authentication (login, signup, logout)
- Real-time EEG prediction via ML models
- Preprocessing and utility services for signal handling
- API endpoints for frontend interaction
- Modular codebase with clean service separation

---

## 📂 Folder Structure

```bash
.
├── .vscode              # VSCode settings
├── Wifi_Communication   # Arduino Sketch
├── ml_models            # Pre-trained EEG classification models (For Indivitual Users)
├── models               # Pydantic models for DB schema
├── response_models      # Response schemas for API
├── routes               # FastAPI route handlers
├── services             # EEG Handling Services
├── utils                # Utility functions (e.g., preprocessing, I/O)
├── database.py          # DB connection and initialization
├── main.py              # FastAPI app entry point
├── requirements.txt     # Required packages
└── readme.md            # Project documentation
```

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/bci-backend.git
cd bci-backend
```

### 2. Create Virtual Environment (Optional)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Server

```bash
uvicorn main:app --reload
```

Backend API will be available at `http://localhost:8000`

---

## ⚙️ Tech Stack

- **Framework**: FastAPI
- **Machine Learning**: scikit-learn / TensorFlow / Keras
- **Database**: MongoDB
- **Communication**: HTTP APIs / Optional WebSocket

---

## 🔐 Authentication

- JWT-based auth using `/login`, `/signup`, `/logout`
- Token required for accessing protected endpoints

---

## 🧠 ML Models

- Pre-trained models for EEG signal classification stored in `ml_models/`
- Easily replaceable with your own models

---

## 📄 API Overview

- `POST /login` – User login
- `POST /signup` – New user registration
- `WS /predict` – Predict class from EEG input
- `GET /dashboard` – Retrieve user interaction history

---

## 🧠 Related Projects

- [BCI Frontend (Next.js)](https://github.com/yourusername/bci-frontend)

---

