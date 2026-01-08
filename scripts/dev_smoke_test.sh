#!/bin/bash
set -e

API_URL="${API_URL:-http://localhost:8080}"
MAX_WAIT_SECONDS=300
POLL_INTERVAL=2

echo "=== Starting Docker Compose ==="
docker compose up -d

echo "=== Waiting for services to be ready ==="
sleep 5

echo "=== Checking /v1/health endpoint ==="
for i in {1..30}; do
    if curl -s -f "${API_URL}/v1/health" > /dev/null; then
        echo "Health check passed"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: Health check failed after 30 attempts"
        docker compose logs api
        exit 1
    fi
    echo "Waiting for API to be ready... (attempt $i/30)"
    sleep 1
done

echo "=== Creating a new job ==="
JOB_RESPONSE=$(curl -s -X POST "${API_URL}/v1/jobs" \
    -H "Content-Type: application/json" \
    -d '{
        "source_repo_url": "https://github.com/octocat/Hello-World",
        "target_repo_url": "https://github.com/octocat/Hello-World",
        "backend_stack": "python",
        "db_stack": "postgres",
        "commit_mode": "pr"
    }')

JOB_ID=$(echo "$JOB_RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
    echo "ERROR: Failed to create job. Response: $JOB_RESPONSE"
    exit 1
fi

echo "Job created with ID: $JOB_ID"

echo "=== Polling job status ==="
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT_SECONDS ]; do
    STATUS_RESPONSE=$(curl -s "${API_URL}/v1/jobs/${JOB_ID}")
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    STAGE=$(echo "$STATUS_RESPONSE" | grep -o '"stage":"[^"]*' | cut -d'"' -f4)
    
    echo "Job status: $STATUS, stage: $STAGE (elapsed: ${ELAPSED}s)"
    
    if [ "$STATUS" = "DONE" ] || [ "$STATUS" = "FAILED" ]; then
        echo "Job reached final state: $STATUS"
        break
    fi
    
    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT_SECONDS ]; then
    echo "ERROR: Job did not complete within ${MAX_WAIT_SECONDS} seconds"
    exit 1
fi

echo "=== Fetching artifact list ==="
ARTIFACTS_RESPONSE=$(curl -s "${API_URL}/v1/jobs/${JOB_ID}/artifacts")
echo "$ARTIFACTS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ARTIFACTS_RESPONSE"

echo "=== Smoke test completed ==="
if [ "$STATUS" = "FAILED" ]; then
    echo "WARNING: Job failed. Check logs for details."
    docker compose logs worker --tail=50
    exit 1
else
    echo "SUCCESS: Job completed successfully"
    exit 0
fi


