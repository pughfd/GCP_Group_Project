README.md 
🏙️ City Events Finder

> INFO 520 Data Communications — EXTRA CREDIT GCP Cloud Infrastructure Project  
> *A serverless, load-balanced web application aggregating events across multiple APIs into a single unified view.*

📌 Project Overview
City Events Finder is a lightweight, serverless web application deployed on **Google Cloud Platform (GCP)**. It fetches real-time event and venue data from multiple external sources, merges and de-duplicates matching records, and enriches listings with live weather conditions.

🌟 Key Features
**Multi-Source Event Aggregation:** Combines listings from Ticketmaster, SeatGeek, and Open-Meteo APIs.
**Serverless Execution:** Deployed as isolated microservice containers on **GCP Cloud Run**.
**Zero-Trust & Access Control:** External API keys stored in **GCP Secret Manager** and dynamically injected at runtime via dedicated IAM Service Accounts.
**Cost & Traffic Optimization:** Configured with `min-instances = 0` to maintain zero cost while idle, fronted by an **External HTTP(S) Load Balancer** with a **Serverless NEG**.

 📐 Architecture & Data Flow
Inbound User Request
│
▼
External HTTP(S) Load Balancer
│ (Serverless NEG)
▼
GCP Cloud Run Service: city-events-app  ───► (Reads Keys via IAM) ───► GCP Secret Manager
│
├───────────────────────┼───────────────────────┐
▼                       ▼                       ▼
Ticketmaster API     Serp API Google Events      Open-Meteo Weather API


📁 Repository Structure
```text
├── app/
│   ├── main.py              # Flask backend logic & API data merging
│   ├── templates/           # Lightweight HTML frontend
│   └── requirements.txt     # Python dependencies
├── scripts/
│   ├── setup_secrets.sh     # GCP Secret Manager & IAM configuration script
│   └── deploy_cloudrun.sh   # Artifact Registry build & Cloud Run deployment
├── Dockerfile               # Container build configuration (Exposes Port 8080)
├── TROUBLESHOOTING.md       # Team incident log & resolution history
└──README.md                # Project documentation
└──savingtime.md
🚀 Quick Start & Local Testing
Prerequisites
Python 3.11+
Docker Desktop
Google Cloud SDK (gcloud)
1. Clone & Set Up Environment
git clone https://github.com/[your-username]/city-events-finder.git
cd city-events-finder/app
pip install -r requirements.txt
2. Set Local Environment Variables
export TICKETMASTER_API_KEY="your_local_key"
export SERPAPI_API_KEY="your_local_key"
python main.py
Access the app locally at http://localhost:8080.
☁️ Google Cloud Deployment
1. Secret & IAM Setup
Run the initial provisioning script to store keys in Secret Manager and assign least-privilege service account roles:
bash scripts/setup_secrets.sh
2. Build & Deploy Container
Build the container image, push to GCP Artifact Registry, and deploy to Cloud Run:
# Build & Push
gcloud builds submit --tag us-central1-docker.pkg.dev/[PROJECT_ID]/city-events-repo/city-events-app:v1

# Deploy to Cloud Run
gcloud run deploy city-events-service \
    --image us-central1-docker.pkg.dev/[PROJECT_ID]/city-events-repo/city-events-app:v1 \
    --region us-central1 \
    --min-instances 0 \
    --max-instances 5 \
    --set-secrets "TICKETMASTER_API_KEY=TICKETMASTER_API_KEY:latest,SEATGEEK_API_KEY=SEATGEEK_API_KEY:latest"

👥 Team & Roles 
Elisa Hartl:  Governance & Cloud Management (IAM Policies, Secret Manager Integration, Load Balancer NEG Wiring, Architecture Documentation).
Franklin Pugh: Technical & Development (Flask Backend API Merging Logic, Dockerization, Artifact Registry Pipeline, Deployment Scripts).

📜 License & Acknowledgments
Built for INFO 520 Data Communications (Fall 2026) at Virginia Commonwealth University. Powered by Google Cloud Platform.
Gemini assistance for Read.me template, html template full citation:
Google. (2026, November 18).HTML5 and CSS starter template and frontend search interface for City Events Finder [Generative AI chat]. Gemini. https://gemini.google.com 
"Write a clean, modern HTML5 and CSS starter template for an index.html university project"


