# DiaBot Backend

AI-Powered Diabetes Screening Platform built with Python/Flask.

## Overview

DiaBot is a dual-approach system combining:
1. **Prediction Module**: LightGBM machine learning for diabetes risk detection (98.1% accuracy)
2. **Advisory Module**: LLM-powered chatbot for context-aware health advice

## Project Structure

```
backend/
├── __init__.py              # Package initialization
├── app.py                   # Application factory
├── run.py                   # Server entry point
├── requirements.txt         # Python dependencies
│
├── config/                  # Configuration module
│   ├── __init__.py
│   └── settings.py          # Environment-specific configs
│
├── models/                  # Database models
│   ├── __init__.py
│   ├── base.py              # SQLAlchemy base
│   ├── diagnostic.py        # Diagnostic results model
│   ├── chat.py              # Chat conversation models
│   └── blockchain.py        # Blockchain audit trail
│
├── services/                # Business logic layer
│   ├── __init__.py
│   ├── database_service.py  # Database operations
│   ├── chatbot_service.py   # AI chatbot (Advisory Module)
│   ├── gemini_service.py    # LLM integration
│   ├── blockchain_service.py # Audit trail
│   └── explanation_service.py # Result explanations
│
├── ml/                      # Machine learning (Prediction Module)
│   ├── __init__.py
│   └── prediction_bridge.py # Model interface
│
└── api/                     # API routes
    ├── __init__.py
    ├── main_routes.py       # Web routes
    └── api_routes.py        # REST API endpoints
```

## Modules

### 1. User Module
- Session-based authentication
- Profile management
- Screening history tracking

### 2. Prediction Module
- **Primary**: Diabetes risk prediction using LightGBM
  - 98.1% accuracy on UCI Early Stage Diabetes dataset
  - 16 symptom-based features (non-invasive)
  - 0.06ms inference time
- Additional: Heart disease, dermatology, breast cancer screening

### 3. Advisory Module
- AI-powered chatbot (Dr. DiaBot)
- Context-aware advice based on prediction results
- Personalized dietary and lifestyle recommendations

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```env
FLASK_ENV=development
SESSION_SECRET=your-secret-key-here
DATABASE_URL=sqlite:///instance/diabot.db
GEMINI_API_KEY=your-gemini-api-key
```

### 3. Run the Server

```bash
# From project root
python -m backend.run

# Or directly
python backend/run.py
```

The server will start at `http://localhost:5000`

## API Endpoints

### Health Check
```
GET /api/v1/health
```

### Diabetes Prediction (Primary)
```
POST /api/v1/predict/diabetes
Content-Type: application/json

{
    "Age": 45,
    "Gender": "Male",
    "Polyuria": "Yes",
    "Polydipsia": "Yes",
    "sudden_weight_loss": "No",
    "weakness": "Yes",
    "Polyphagia": "No",
    "Genital_thrush": "No",
    "visual_blurring": "Yes",
    "Itching": "No",
    "Irritability": "No",
    "delayed_healing": "No",
    "partial_paresis": "No",
    "muscle_stiffness": "No",
    "Alopecia": "No",
    "Obesity": "No"
}
```

### Chatbot (Advisory Module)
```
POST /api/v1/chat
Content-Type: application/json

{
    "message": "What should I eat if I have high diabetes risk?",
    "conversation_history": [],
    "diagnostic_context": {
        "result_type": "diabetes",
        "risk_level": "High Risk"
    }
}
```

## Technology Stack

- **Framework**: Flask 3.x
- **Database**: SQLAlchemy with SQLite
- **ML**: LightGBM, scikit-learn, TensorFlow
- **LLM**: Google Gemini API
- **Python**: 3.11+

## Medical Disclaimer

This system is designed as a screening aid, not a replacement for clinical diagnosis by a certified medical professional.
