EuroRail AI Assistant (CrewAI Multi-Agent System)

An AI-powered rail booking platform that combines RAG (Retrieval), Machine Learning, and CrewAI multi-agent orchestration to deliver intelligent train search, booking, and decision-making.

 Key Features
 Train Search (RAG-Based)
Search trains by:
Route (e.g., Paris → Berlin)
Date
Provider (SNCF, DB, Eurostar, etc.)
Filters:
Cheapest / Fastest
Direct / Connection
Seat availability
WiFi availability
 Seat Selection
Real train-style layout (A/B/C/D)
Multi-seat selection supported
Interactive UI
 Ticket Booking
Booking ID & PNR generation
Multi-passenger support
Clean booking summary
PDF Ticket + QR Code
Downloadable ticket
QR-based validation
 Email Integration
Send ticket PDF via email
 AI Assistant (Core)

Ask queries like:

"Is SNCF available from Paris to Lyon on 2026-05-01?"
"Show cheapest trains from Amsterdam to Berlin"
"Should I book Paris to Berlin today or later?"

 Returns real data (no hallucination)
 Displays:

Train name + number
Date
Route
Seats
Price
Status
 CrewAI Multi-Agent Architecture

This project uses CrewAI to orchestrate multiple intelligent agents.

 Agents
 Search Agent
Retrieves train data (RAG-style from CSV)
Handles route, date, provider filtering

 Price Agent (ML)
Predicts future price trends
Recommends:
BOOK NOW
WAIT

 Sell-Out Agent
Predicts seat availability risk
Labels:
LOW / MEDIUM / HIGH

 Response Agent
Combines outputs from all agents
Produces final structured response

 Flow
User Query
   ↓
Search Agent (RAG)
   ↓
Price Agent (ML)
   ↓
Sell-out Agent
   ↓
Response Agent
   ↓
Final Answer

 Machine Learning
Model: RandomForest / ExtraTrees
Task: Price prediction & booking recommendation
Features:
Seats availability
Demand level
Booking timing
Route & provider

 Tech Stack
Backend
FastAPI
Python
Pandas
Scikit-learn
Uvicorn
Frontend
React (Vite)
HTML, CSS, JavaScript
AI Layer
CrewAI (multi-agent system)
Groq LLM (Llama 3)
RAG (CSV-based retrieval)

Other
QR Code generation
PDF generation
Email (SMTP)


 Project Structure
EuroRail-AI-Assistant/
│
├── backend/
│   ├── app.py
│   ├── crew_logic.py
│   ├── query_engine.py
│   ├── price_predictor.py
│   ├── sellout_model.py
│   ├── data/
│   └── models/
│
├── frontend/
│   ├── src/
│   ├── App.jsx
│   └── components/
│
├── README.md
└── .gitignore
 Setup & Run
1️ Clone Repo
git clone https://github.com/PentyalaHarshit/EuroRail-AI-Assistant.git
cd EuroRail-AI-Assistant
2️ Backend
cd backend
pip install -r requirements.txt
py -3.11 -m uvicorn app:app --reload

 Open:

http://127.0.0.1:8000/docs
3️ Frontend
cd frontend
npm install
npm run dev

 Open:

http://localhost:5173
Environment Variables

Create file: backend/.env

GROQ_API_KEY=your_groq_api_key
EMAIL_USER=your_email@gmail.com
EMAIL_APP_PASSWORD=your_app_password

 Do NOT push .env to GitHub

 Example Queries
“Is SNCF available from Paris to Lyon?”
“Show fastest trains from Berlin to Munich”
“Should I book Paris to Berlin today or later?”
“Which train will sell out soon?”
 Future Enhancements
Live API integration ( SNCF / DB)
Payment gateway
User login system
Real-time pricing updates
Mobile app version
 Highlights

Multi-Agent AI System (CrewAI)
RAG + ML integration
Real-world booking use case
Full-stack application
Production-style architecture