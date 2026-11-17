#!/bin/sh
# Creates the p4-secrets Secret from the git-ignored .env (values never
# appear in the repository or the manifests).
set -e
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
kubectl get namespace p4-handshake >/dev/null 2>&1 || kubectl create namespace p4-handshake
kubectl -n p4-handshake create secret generic p4-secrets \
  --from-literal=MONGO_USER="${MONGO_USER:-p4admin}" \
  --from-literal=MONGO_PASSWORD="$MONGO_PASSWORD" \
  --from-literal=MONGO_URI="mongodb://${MONGO_USER:-p4admin}:${MONGO_PASSWORD}@p4-mongo.p4-handshake.svc.cluster.local:27017/?authSource=admin" \
  --from-literal=JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
