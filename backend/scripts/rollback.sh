#!/usr/bin/env bash
set -euo pipefail

IMAGE_TAG="${1:?Usage: rollback.sh <image_tag> <environment>}"
ENVIRONMENT="${2:?Usage: rollback.sh <image_tag> <environment>}"
COMPOSE_DIR="/opt/church-finder"

echo "[rollback] Starting rollback → $IMAGE_TAG on $ENVIRONMENT"
echo "[rollback] $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

case "$ENVIRONMENT" in
  prod|staging|dev)
    COMPOSE_FILE="$COMPOSE_DIR/docker-compose.${ENVIRONMENT}.yml"
    ;;
  *)
    echo "[rollback] ERROR: unknown environment '$ENVIRONMENT'"
    exit 1
    ;;
esac

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "[rollback] ERROR: compose file not found: $COMPOSE_FILE"
  exit 1
fi

echo "[rollback] Pulling $IMAGE_TAG …"
docker pull "$IMAGE_TAG"

echo "[rollback] Updating IMAGE_TAG → $IMAGE_TAG"
export IMAGE_TAG

cd "$COMPOSE_DIR"
docker compose -f "$COMPOSE_FILE" up -d --no-deps --pull never backend

echo "[rollback] Waiting for health check …"
RETRIES=10
DELAY=3
for i in $(seq 1 $RETRIES); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[rollback] ✓ Health check passed after $i attempt(s)"
    break
  fi
  if [[ $i -eq $RETRIES ]]; then
    echo "[rollback] ✗ Health check FAILED after $RETRIES attempts"
    exit 1
  fi
  sleep $DELAY
done

echo "[rollback] Pruning unused images …"
docker image prune -f

echo "[rollback] Done — running image: $IMAGE_TAG"
