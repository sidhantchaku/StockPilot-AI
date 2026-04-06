#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-stockpilot-ai}"
ARTIFACT_REPO="${ARTIFACT_REPO:-stockpilot}"
SQL_INSTANCE="${SQL_INSTANCE:-stockpilot-sql}"
SQL_TIER="${SQL_TIER:-db-custom-1-3840}"
DB_NAME="${DB_NAME:-stockpilot}"
DB_USER="${DB_USER:-stockpilot_app}"
DB_PASS="${DB_PASS:-}"
ALLOW_UNAUTH="${ALLOW_UNAUTH:-true}"
RUN_SERVICE_ACCOUNT="${RUN_SERVICE_ACCOUNT:-}"
CLOUDSDK_CONFIG_DIR="${CLOUDSDK_CONFIG:-$(pwd)/.gcloud}"

export CLOUDSDK_CONFIG="${CLOUDSDK_CONFIG_DIR}"
mkdir -p "${CLOUDSDK_CONFIG}"

if [[ -z "${PROJECT_ID}" ]]; then
  PROJECT_ID="$(gcloud config get-value core/project 2>/dev/null || true)"
fi
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "PROJECT_ID is required. Example:"
  echo "  PROJECT_ID=my-gcp-project REGION=us-central1 ./deploy/deploy_cloudrun.sh"
  exit 1
fi

if [[ -z "${DB_PASS}" ]]; then
  DB_PASS="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
fi

echo "Using project: ${PROJECT_ID}"
echo "Using region:  ${REGION}"
gcloud config set project "${PROJECT_ID}" >/dev/null

echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com >/dev/null

echo "Ensuring Artifact Registry repo exists..."
if ! gcloud artifacts repositories describe "${ARTIFACT_REPO}" --location "${REGION}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${ARTIFACT_REPO}" \
    --location "${REGION}" \
    --repository-format docker \
    --description "Docker repo for StockPilot AI"
fi

echo "Ensuring Cloud SQL instance exists..."
if ! gcloud sql instances describe "${SQL_INSTANCE}" >/dev/null 2>&1; then
  gcloud sql instances create "${SQL_INSTANCE}" \
    --database-version=POSTGRES_15 \
    --tier="${SQL_TIER}" \
    --region="${REGION}" \
    --storage-size=20GB \
    --storage-type=SSD \
    --availability-type=ZONAL \
    --backup
fi

echo "Ensuring database exists..."
if ! gcloud sql databases describe "${DB_NAME}" --instance "${SQL_INSTANCE}" >/dev/null 2>&1; then
  gcloud sql databases create "${DB_NAME}" --instance "${SQL_INSTANCE}"
fi

echo "Ensuring DB user exists..."
if ! gcloud sql users list --instance "${SQL_INSTANCE}" --format='value(name)' | grep -q "^${DB_USER}$"; then
  gcloud sql users create "${DB_USER}" --instance "${SQL_INSTANCE}" --password "${DB_PASS}"
else
  gcloud sql users set-password "${DB_USER}" --instance "${SQL_INSTANCE}" --password "${DB_PASS}" >/dev/null
fi

CONN_NAME="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"
DB_URL="postgresql+psycopg2://${DB_USER}:${DB_PASS}@/${DB_NAME}?host=/cloudsql/${CONN_NAME}"

echo "Saving DB URL in Secret Manager..."
if ! gcloud secrets describe "${SERVICE_NAME}-db-url" >/dev/null 2>&1; then
  gcloud secrets create "${SERVICE_NAME}-db-url" --replication-policy="automatic"
fi
printf "%s" "${DB_URL}" | gcloud secrets versions add "${SERVICE_NAME}-db-url" --data-file=-

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
if [[ -z "${RUN_SERVICE_ACCOUNT}" ]]; then
  RUN_SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi

echo "Granting IAM roles to runtime service account (${RUN_SERVICE_ACCOUNT})..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUN_SERVICE_ACCOUNT}" \
  --role="roles/cloudsql.client" >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUN_SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" >/dev/null

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/${SERVICE_NAME}:$(date +%Y%m%d-%H%M%S)"

echo "Building image with Cloud Build: ${IMAGE}"
gcloud builds submit --tag "${IMAGE}" .

DEPLOY_FLAGS=(
  "--image=${IMAGE}"
  "--region=${REGION}"
  "--platform=managed"
  "--service-account=${RUN_SERVICE_ACCOUNT}"
  "--add-cloudsql-instances=${CONN_NAME}"
  "--set-secrets=DATABASE_URL=${SERVICE_NAME}-db-url:latest"
  "--set-env-vars=PYTHONUNBUFFERED=1"
  "--memory=2Gi"
  "--cpu=2"
  "--port=8080"
  "--min-instances=0"
  "--max-instances=5"
)

if [[ "${ALLOW_UNAUTH}" == "true" ]]; then
  DEPLOY_FLAGS+=("--allow-unauthenticated")
else
  DEPLOY_FLAGS+=("--no-allow-unauthenticated")
fi

echo "Deploying Cloud Run service..."
gcloud run deploy "${SERVICE_NAME}" "${DEPLOY_FLAGS[@]}"

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format='value(status.url)')"
echo
echo "Deployment complete."
echo "Service URL: ${SERVICE_URL}"
echo "Cloud SQL:   ${CONN_NAME}"
