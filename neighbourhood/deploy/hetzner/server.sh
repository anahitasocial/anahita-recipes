#!/bin/sh
# Makes the site's server at Hetzner with its CLI, hcloud: a firewall open
# to SSH, 80 and 443 alone, your SSH key, and one Ubuntu server. Not tried
# yet with Anahita: tell us how it went, in an issue on anahita-recipes.
#
#   deploy/hetzner/server.sh <domain> [public key file]
#
# Needs hcloud, with a context made for your project (hcloud context
# create). TYPE is cax11 (2 ARM vCPU, 4 GB, 40 GB) unless said; LOCATION is
# fsn1 (Falkenstein) unless said: nbg1 Nuremberg, hel1 Helsinki. When cax11
# cannot be ordered, as has happened, `hcloud server-type list` shows the
# others: any with 2 vCPU and 4 GB will do. BACKUPS=on
# turns on Hetzner's daily backups, for a fifth more a month.
#
# Safe to run again: what is there already is left as it is.
set -eu
DOMAIN=${1:?the domain of the site}
KEY_FILE=${2:-$HOME/.ssh/id_ed25519.pub}
TYPE=${TYPE:-cax11}
LOCATION=${LOCATION:-fsn1}
NAME=$(printf '%s' "$DOMAIN" | tr . -)
command -v hcloud >/dev/null || { echo "hcloud is needed: https://github.com/hetznercloud/cli" >&2; exit 1; }
test -f "$KEY_FILE" || { echo "No public key at $KEY_FILE: name one." >&2; exit 1; }

if ! hcloud ssh-key describe "$NAME" >/dev/null 2>&1; then
  hcloud ssh-key create --name "$NAME" --public-key-from-file "$KEY_FILE"
fi

if ! hcloud firewall describe "$NAME" >/dev/null 2>&1; then
  hcloud firewall create --name "$NAME"
  for port in 22 80 443; do
    hcloud firewall add-rule "$NAME" --direction in --protocol tcp --port "$port" \
      --source-ips 0.0.0.0/0 --source-ips ::/0
  done
fi

if ! hcloud server describe "$NAME" >/dev/null 2>&1; then
  hcloud server create --name "$NAME" --type "$TYPE" --image ubuntu-24.04 \
    --location "$LOCATION" --ssh-key "$NAME" --firewall "$NAME"
fi
[ "${BACKUPS:-}" = on ] && hcloud server enable-backup "$NAME"

echo "The server is at $(hcloud server ip "$NAME"); sign in as root. Next: point the"
echo "five DNS names at it (deploy/README.md), then make init."
