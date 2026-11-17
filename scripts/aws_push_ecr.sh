#!/bin/sh
# Builds the seven images, creates the p4-* ECR repositories if needed,
# logs Docker in to ECR with a short-lived token, and pushes tag 2.0.
#   AWS_REGION=us-west-2 ./scripts/aws_push_ecr.sh
set -e
cd "$(dirname "$0")/.."
REGION=${AWS_REGION:-us-west-2}
TAG=${TAG:-2.0}
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

for name in p4-student-service p4-company-service p4-job-service p4-application-service \
            p4-event-service p4-assistant-service p4-frontend; do
  aws ecr describe-repositories --region "$REGION" --repository-names "$name" >/dev/null 2>&1 || \
    aws ecr create-repository --region "$REGION" --repository-name "$name" \
      --image-scanning-configuration scanOnPush=true >/dev/null
done

# EKS nodes are x86_64: build for linux/amd64 even on an Apple-silicon Mac.
for svc in student company job application event assistant; do
  docker buildx build --platform linux/amd64 -f backend/docker/Dockerfile.$svc \
    -t "$REGISTRY/p4-$svc-service:$TAG" --push backend
done
docker buildx build --platform linux/amd64 -f frontend/docker/Dockerfile \
  -t "$REGISTRY/p4-frontend:$TAG" --push frontend

echo "Pushed to $REGISTRY. Next: ECR_REGISTRY=$REGISTRY ./scripts/aws_deploy_eks.sh"
