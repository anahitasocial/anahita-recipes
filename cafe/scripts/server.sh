#!/bin/sh
# make server: readies a new Ubuntu server for the site, over SSH, then
# brings its kubeconfig here. Safe to run again: each step is skipped when
# it has been done.
#
#   1. A 2 GB swap file, so that a busy moment does not stop a service.
#   2. k3s, at K3S_VERSION, with its Traefik, which takes the web's
#      connections.
#   3. Traefik told to keep visitors' addresses (anahita-services'
#      k8s/k3s/traefik-config.yml).
#   4. cert-manager, at CERT_MANAGER_VERSION, which gets the certificates.
#   5. The kubeconfig, in KUBECONFIG_FILE, readable by you alone, pointing
#      at the tunnel (make tunnel), never at the server's own port.
#
#   scripts/server.sh <user@server> <kubeconfig file> <context name>
set -eu
TARGET=${1:?user@server}
KUBECONFIG_FILE=${2:?the kubeconfig file to write}
CONTEXT=${3:?the context name}
: "${K3S_VERSION:?}" "${CERT_MANAGER_VERSION:?}" "${ANAHITA_VERSION:?}" "${TUNNEL_PORT:?}"

echo "Readying $TARGET: swap, k3s $K3S_VERSION, cert-manager $CERT_MANAGER_VERSION"
ssh "$TARGET" "sudo K3S_VERSION='$K3S_VERSION' CERT_MANAGER_VERSION='$CERT_MANAGER_VERSION' ANAHITA_VERSION='$ANAHITA_VERSION' bash -s" <<'REMOTE'
set -euo pipefail
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  echo '/swapfile none swap defaults 0 0' >> /etc/fstab
  sysctl -qw vm.swappiness=10
  echo 'vm.swappiness=10' > /etc/sysctl.d/90-swap.conf
  echo "swap: 2 GB"
fi
if ! command -v k3s >/dev/null; then
  curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="$K3S_VERSION" sh -s - server \
    --write-kubeconfig-mode 600 \
    --kubelet-arg=fail-swap-on=false
fi
until k3s kubectl get nodes 2>/dev/null | grep -q ' Ready'; do sleep 3; done
echo "k3s: ready"
k3s kubectl apply -f "https://raw.githubusercontent.com/anahitasocial/anahita-services/$ANAHITA_VERSION/k8s/k3s/traefik-config.yml"
k3s kubectl apply -f "https://github.com/cert-manager/cert-manager/releases/download/$CERT_MANAGER_VERSION/cert-manager.yaml" >/dev/null
k3s kubectl -n cert-manager rollout status deployment/cert-manager-webhook --timeout=300s
echo "cert-manager: ready"
REMOTE

# The kubeconfig, its server the tunnel's end here, its names the site's.
mkdir -p "$(dirname "$KUBECONFIG_FILE")"
umask 077
ssh "$TARGET" "sudo cat /etc/rancher/k3s/k3s.yaml" \
  | sed -e "s|https://127.0.0.1:6443|https://127.0.0.1:$TUNNEL_PORT|" -e "s|: default$|: $CONTEXT|" \
  > "$KUBECONFIG_FILE"
echo "The kubeconfig is in $KUBECONFIG_FILE, as context $CONTEXT."
echo "Next: make tunnel, in a terminal of its own; then make apply."
