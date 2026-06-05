# Keycloak + GCP WIF + Gemini PoC

This Proof of Concept demonstrates how a local Python application can authenticate to Google Cloud Platform using an OpenID Connect (OIDC) token issued by Keycloak, without requiring any long-lived local GCP Service Account JSON keys.

## Architecture

1. **Local App** requests an OAuth2/OIDC token from **Keycloak**.
2. **Local App** writes this token to a local file (`keycloak_token.txt`).
3. The **Google Cloud Python SDK** reads the `client-config.json` (pointed to by `GOOGLE_APPLICATION_CREDENTIALS`).
4. Based on the config, the SDK reads `keycloak_token.txt`, asks GCP **Workload Identity Federation (WIF)** to exchange it for a short-lived GCP STS token, and then impersonates a specific **Verex AI Service Account**.
5. The local app calls the **Gemini API** on Vertex AI securely.

---

## Step 0: Run Keycloak Locally (Docker)

To run Keycloak locally for this PoC, a `docker-compose.yml` file is provided.

1. Ensure Docker is running.
2. Start Keycloak in development mode:
   ```bash
   docker compose up -d
   ```
3. Access the Keycloak Admin Console at [http://localhost:8080/admin](http://localhost:8080/admin) and log in with username `admin` and password `admin`.

---

## Step 1: Keycloak Setup

> **⚠️ CRITICAL FOR LOCAL TESTING:** Workload Identity Federation requires your Identity Provider (Keycloak) to be accessible over the public internet via HTTPS so GCP can fetch its public signing keys. 
> 
> Because Keycloak is running on `localhost`, you **must** use a tool like `ngrok` to expose it:
> 1. Run `ngrok http 8080`
> 2. Note the public HTTPS URL (e.g., `https://abc-123.ngrok.app`).
> 3. Log into the Keycloak Admin Console using the **ngrok URL** (not localhost). This ensures Keycloak uses the correct hostnames.

1. **Realm, Client, and Secrets are auto-provisioned.** By starting Keycloak using the provided `docker-compose.yml`, the Realm (`gcp-poc`), Client (`gcp-wif-client`), and Secret (`my-super-secret-client-secret`) are automatically configured via `realm-import.json`.
2. The `audience-mapper` is already included to ensure the token has an `aud` claim compatible with GCP WIF.

---

## Step 2: GCP WIF & IAM Setup

Open your terminal and authenticate to GCP (`gcloud auth login`). Make sure you have the required permissions (`roles/iam.workloadIdentityPoolAdmin` and `roles/iam.serviceAccountAdmin`).

### 1. Set environment variables
```bash
export PROJECT_ID="project-2db91b7b-2a47-4e55-b14"
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud config set project $PROJECT_ID
```

### 2. Create the Service Account to be impersonated
```bash
export SA_NAME="gemini-caller-sa"
gcloud iam service-accounts create $SA_NAME --display-name="SA for Gemini Caller"

# Grant it Vertex AI User permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### 3. Create Workload Identity Pool and Provider
```bash
export POOL_ID="keycloak-pool"
export PROVIDER_ID="keycloak-provider"

# Create Pool
gcloud iam workload-identity-pools create $POOL_ID \
  --location="global" \
  --description="Pool for Keycloak" \
  --display-name="Keycloak Pool"

# Create OIDC Provider matching your Keycloak issuer
# Issuer URL looks like: https://your-keycloak-domain/realms/YOUR_REALM
export KEYCLOAK_ISSUER_URI="https://blustery-pessimist-unlovely.ngrok-free.dev/realms/gcp-poc"

gcloud iam workload-identity-pools providers create-oidc $PROVIDER_ID \
  --location="global" \
  --workload-identity-pool=$POOL_ID \
  --issuer-uri="$KEYCLOAK_ISSUER_URI" \
  --allowed-audiences="gcp-wif-client" \
  --attribute-mapping="google.subject=assertion.sub" \
  --display-name="Keycloak OIDC Provider"
```
*(Note: Replace `gcp-wif-client` with the `aud` value present in your Keycloak token).*

### 4. Authorize Keycloak Identities to Impersonate the SA
Allow any identity authenticated in the pool to impersonate our Service Account:
```bash
gcloud iam service-accounts add-iam-policy-binding ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/*"
```

### 5. Generate the Client Configuration File
This file is used by the Python SDK locally.
```bash
gcloud iam workload-identity-pools create-cred-config \
    projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID} \
    --service-account="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --output-file="client-config.json" \
    --credential-source-file="keycloak_token.txt" \
    --credential-source-type="text"
```
Keep the generated `client-config.json` in your local directory.

---

## Step 3: Run the Python App

1. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your details:
```bash
cp .env.example .env
```
Edit `.env` inserting your Keycloak URL, Client ID, Client Secret, and GCP Project ID.

3. Fetch the OIDC Token from Keycloak:
```bash
python fetch_token.py
```
This saves the token to `keycloak_token.txt`.

4. Call Vertex AI (Gemini):
```bash
python main.py
```

If everything is configured correctly, `main.py` will read the auth flow automatically through `client-config.json` -> `keycloak_token.txt`, swap it for GCP credentials in the background, and print the response from the Gemini model!