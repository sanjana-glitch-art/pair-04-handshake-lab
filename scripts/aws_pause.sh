#!/bin/sh
# Pause (cost control) or resume the EKS deployment without deleting code,
# manifests, data volumes, or evidence. The control plane, NAT gateway, and
# load balancer still bill while paused; delete the cluster when done.
#   ./scripts/aws_pause.sh pause    scale the node group to 0 (EBS volumes stay)
#   ./scripts/aws_pause.sh resume   scale back up and wait for the pods
set -e
case "$1" in
  pause)
    eksctl scale nodegroup --cluster p4-handshake --name p4-nodes --nodes 0 --nodes-min 0 ;;
  resume)
    eksctl scale nodegroup --cluster p4-handshake --name p4-nodes --nodes 1 --nodes-min 0
    kubectl -n p4-handshake wait --for=condition=available deploy --all --timeout=900s
    kubectl -n p4-handshake get pods,svc ;;
  *) echo "usage: $0 pause|resume"; exit 1 ;;
esac
