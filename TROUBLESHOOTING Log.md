MARK EACH: ✅ Resolved / ⏳ Open

### ["the" Coupling Event Issue] ⏳ Open
- **Nov 18
- **Component:** Decoupling python scripting (line )
- **Error Log / Output:** Events with venue or title name start with "The" incorrectly coupled when actually distinct events
- **Fix / Solution:** in progress, may leave due to time constraint & focus on Cloud Run deployment phase
- **Owner:** Elisa

### [Short Name of Issue] ⏳ Open
- **Date/Time:**
- **GCP Component:** (Cloud Run / Load Balancer / Secret Manager / Artifact Registry)
- **Error Log / Output:**
- **Fix / Solution:**
- **Owner:**

### [Short Name of Issue] ⏳ Open
- **Date/Time:**
- **GCP Component:** (Cloud Run / Load Balancer / Secret Manager / Artifact Registry)
- **Error Log / Output:**
- **Fix / Solution:**
- **Owner:**

MARK EACH: ✅ Resolved/ ⏳ Open

Deployment & Infrastructure Specific Troubleshooting Log — November 20, 2026
1. ✅Missing Local gcloud CLI in WSL
 * Symptom: The gcloud CLI was not installed in the local WSL development environment during the deployment sprint.
 * Root Cause: Local environment was set up for Python/Git development without the Google Cloud SDK or local Docker Desktop.
 * Resolution: Pivoted to GCP Cloud Shell (which comes pre-configured with gcloud and git), cloned the GitHub repository over HTTPS, and used Cloud Build (gcloud builds submit) to build the Dockerfile and push the container image directly to Artifact Registry (events-repo).
2. ✅Malformed Load Balancer Test URL (/80 Path Suffix)
 * Symptom: Navigating to [http://136.81.10.80/80](http://136.81.10.80/80) in Chrome failed to load the application.
 * Root Cause: Appending /80 sent an HTTP path request for /80 rather than targeting port 80 (HTTP defaults to port 80 automatically; explicit ports use :80).
 * Resolution: Removed /80 and accessed the application via plain [http://136.81.10.80/](http://136.81.10.80/) and [http://136.81.10.80/health](http://136.81.10.80/health).
3. ✅$0.00 Spend Cap Triggering a Project-Wide Billing Pause (500 / 503 Outage)
 * Symptom: After provisioning the Global External Application Load Balancer and Serverless NEG (events-neg), both the Load Balancer IP (136.81.10.80) and the direct Cloud Run URL returned 503 Service Unavailable. Cloud Logging recorded an HTTP 500 error (2026-11-20T16:58:20Z) with the payload: "The request failed because billing is disabled for this project."
 * Root Cause: The project's billing budget (EXTRA CREDIT NO SPEND CAP, managed under the teammate's billing account) was configured with a $0.00 spend cap. Because GCP spend caps evaluate gross estimated usage before applying free-tier credits, the first live traffic at 11:44 AM immediately enforced the cap and paused Cloud Run.
 * Resolution: Switched to the managing billing account view in Billing → Budgets & caps, lifted the enforced spend cap, verified billingEnabled: true via gcloud billing projects describe, and replaced the spend cap with a $10.00 monthly alerts-only budget with email alert thresholds (spend cap status set to Not applicable).
4. ✅Intermittent 200 / 503 Flapping During Post-Spend-Cap Recovery
 * Symptom: After lifting the spend cap, requests flapped between 200 OK (on initial curl checks and briefly after forcing a fresh Cloud Run revision, city-events-finder-00002-tks) and 503 Service Unavailable across Chrome Incognito, local WSL, and Cloud Shell.
 * Root Cause: Documented Google Cloud Run recovery delay following a lifted spend cap. Although Cloud Run's control plane reported Ready, ConfigurationsReady, and RoutesReady as True, events-neg was properly attached to events-backend-service, and Cloud Logging showed zero container crashes, Google Frontend edge proxies took roughly 30–40 minutes to fully clear the billing-pause state.
 * Resolution: Verified healthy container logs and backend wiring, stopped redundant redeployments, and monitored /health via a 20-second curl polling loop until edge recovery completed. Confirmed full end-to-end stability on [http://136.81.10.80/](http://136.81.10.80/) (landing page, /health, and live city event/weather searches).
5. ✅Upstream SerpAPI Read Timeout (Graceful Degradation Verified)
 * Symptom: Cloud Run logs (2026-11-20 16:39:57 UTC) recorded ERROR in app: SerpAPI error: HTTPSConnectionPool(host='serpapi.com', port=443): Read timed out. (read timeout=10).
 * Root Cause: Transient upstream latency from the external SerpAPI endpoint exceeded the configured 10-second request timeout.
 * Resolution: Confirmed that the Flask backend's exception handling caught the timeout cleanly without crashing Gunicorn, returning HTTP 200 on /api/events?city=Richmond%2C%20VA with Ticketmaster and Open-Meteo data intact.



