#!/bin/sh
# Applies the p4-handshake namespace and manifests to EKS with ECR images,
# creates the Secret from .env, seeds MongoDB, and prints the public URL.
#   ECR_REGISTRY=<account>.dkr.ecr.us-west-2.amazonaws.com ./scripts/aws_deploy_eks.sh
set -e
cd "$(dirname "$0")/.."
: "${ECR_REGISTRY:?set ECR_REGISTRY (printed by aws_push_ecr.sh)}"
aws eks update-kubeconfig --name p4-handshake --region "${AWS_REGION:-us-west-2}"

./scripts/k8s_secrets.sh
TMP=$(mktemp -d)
cp -R k8s "$TMP/"
sed -i.bak "s#ECR_REGISTRY#$ECR_REGISTRY#g" "$TMP/k8s/overlays/aws/kustomization.yaml"
kubectl apply -k "$TMP/k8s/overlays/aws"
rm -rf "$TMP"

kubectl -n p4-handshake wait --for=condition=complete job/p4-kafka-topics --timeout=600s
kubectl -n p4-handshake rollout status statefulset/p4-mongo --timeout=600s

# Seed through a temporary port-forward (credentials stay in .env).
kubectl -n p4-handshake port-forward svc/p4-mongo 27057:27017 >/dev/null 2>&1 &
PF=$!; sleep 4
set -a; . ./.env; set +a
MONGO_URI="mongodb://${MONGO_USER:-p4admin}:${MONGO_PASSWORD}@localhost:27057/?authSource=admin&directConnection=true" \
  backend/.venv/bin/python database/seed/generate_seed.py --reset
kill $PF

kubectl -n p4-handshake get pods,svc
echo "Frontend: http://$(kubectl -n p4-handshake get svc p4-frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'):9040"
