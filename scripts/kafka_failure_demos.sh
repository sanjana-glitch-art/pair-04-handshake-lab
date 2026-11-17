#!/bin/sh
# Runs the three Kafka failure cases against the p4-handshake cluster and
# prints evidence (output is saved to docs/evidence/kafka_failures.log).
#   ./scripts/kafka_failure_demos.sh
set -e
NS=p4-handshake
EXEC="kubectl -n $NS exec deploy/p4-application-service --"
worker_logs() { kubectl -n $NS logs -l app=p4-application-worker --tail=200 --prefix 2>/dev/null; }

echo "===== Case 1: same event published twice -> idempotent consumer ====="
$EXEC python -m app.workers.demo duplicate
echo "--- worker log lines:"
worker_logs | grep -E "already processed|already stored|duplicate_skipped" | tail -4

echo
echo "===== Case 2: worker killed during processing -> offset committed only after the write ====="
OUT=$($EXEC python -m app.workers.demo slow); echo "$OUT"
APP_ID=$(echo "$OUT" | sed -n 's/.*APPLICATION_ID=\([0-9]*\).*/\1/p')
VICTIM=""
for i in $(seq 1 20); do
  VICTIM=$(kubectl -n $NS logs -l app=p4-application-worker --tail=20 --prefix | grep "demo pause" | tail -1 | sed 's/^\[pod\/\([^/]*\)\/.*/\1/')
  [ -n "$VICTIM" ] && break; sleep 1
done
echo "--- worker $VICTIM is paused before its database write; killing it now (force, no grace period)"
kubectl -n $NS delete pod "$VICTIM" --grace-period=0 --force 2>&1 | grep -v Warning || true
$EXEC python -m app.workers.demo check "$APP_ID"
echo "--- waiting for the message to be redelivered after the rebalance/restart ..."
START=$(date +%s)
for i in $(seq 1 30); do
  sleep 5
  if $EXEC python -m app.workers.demo check "$APP_ID" | grep -q "result:"; then break; fi
done
echo "--- stored $(( $(date +%s) - START ))s after the kill:"
$EXEC python -m app.workers.demo check "$APP_ID"
echo "--- worker log lines for application $APP_ID:"
worker_logs | grep -E "demo pause|message handled|offset committed" | grep -v '"trace_id": null' | tail -4
kubectl -n $NS get pods -l app=p4-application-worker

echo
echo "===== Case 3: poison message -> bounded retries -> dead-letter topic, pipeline continues ====="
$EXEC python -m app.workers.demo poison
echo "--- worker log lines:"
worker_logs | grep -E "message failed|dead-letter|poison" | tail -5
echo "--- p4.application.created.dlq contents:"
kubectl -n $NS exec p4-kafka-0 -- /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic p4.application.created.dlq --from-beginning --timeout-ms 5000 2>/dev/null | tail -2
