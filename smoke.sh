#!/bin/sh
# Tries one recipe from `make init` to a running site, with this machine as
# its server, as a person would with a server of their own:
#
#   1. make init, answered from here: the domain <recipe>.test, mail to a
#      server that is not there, and this machine as the server.
#   2. make server, over SSH to this machine: swap, k3s, cert-manager.
#   3. make tunnel, left running, then make apply.
#   4. Every service ready, the database's migrations and Garage's setup
#      done, and NodeInfo saying the release the recipe names and offering
#      what its instance.json says.
#
#   ./smoke.sh forum
#
# Made for GitHub's runners (.github/workflows/smoke.yml): it installs an SSH
# server, k3s and cert-manager on the machine it runs on, and keeps them.
# Not for your own computer. What it cannot try: a real domain, Let's
# Encrypt's certificates, mail, and the web app (make web).
set -eu
recipe=${1:?which recipe: ./smoke.sh forum}
domain="$recipe.test"
cd "$(dirname "$0")/$recipe"
[ -f k8s/kustomization.yml ] || { echo "$recipe is not a recipe with a site." >&2; exit 1; }

step() { echo; echo "== $*"; }

step "SSH to this machine, as make server reaches a server"
command -v sshd >/dev/null || sudo apt-get install -y -qq openssh-server >/dev/null
sudo systemctl start ssh
mkdir -p ~/.ssh && chmod 700 ~/.ssh
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N '' -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
ssh-keyscan -H 127.0.0.1 >> ~/.ssh/known_hosts 2>/dev/null

step "make init"
# The answers, in the order init.sh asks: domain, name, email, from,
# support, SMTP server, port, user, password, server, SSH user.
printf '%s\n' "$domain" "Smoke $recipe" "admin@$domain" "noreply@$domain" "support@$domain" \
  "smtp.$domain" 587 "noreply@$domain" "" 127.0.0.1 "$(id -un)" | scripts/init.sh

step "make server"
make server

step "make tunnel, then make apply"
make tunnel > tunnel.log 2>&1 &
for i in $(seq 1 30); do nc -z 127.0.0.1 16443 && break; sleep 1; done
make apply

K="kubectl --kubeconfig $HOME/.kube/$domain.yaml --context $domain -n anahita"

# On a failure from here on: what the cluster was doing, to see why.
why() {
  [ $? = 0 ] && return
  echo; echo "== Why: the pods, the Jobs' logs, the latest events, the machine"
  $K get pods -o wide || true
  for store in mysql redis rabbitmq garage; do
    echo "-- $store"; $K logs "statefulset/$store" --tail=60 --all-containers || true
  done
  echo "-- inside mysql-0: the open-files limits, and what runs"
  $K exec mysql-0 -- sh -c 'echo "soft $(ulimit -n), hard $(ulimit -Hn)"; ps -eo pid,stat,etime,pcpu,args 2>/dev/null || ls /proc | head' || true
  echo "-- k3s and containerd"; k3s --version | head -1; sudo k3s ctr version 2>/dev/null | grep -i version | head -2 || true
  for job in migration-job garage-init; do
    echo "-- $job"; $K logs "job/$job" --tail=20 --all-containers || true
  done
  $K get pods --no-headers | awk '$3 != "Running" && $3 != "Completed" {print $1}' | head -5 | while read -r pod; do
    echo "-- $pod"; $K describe pod "$pod" | tail -25 || true
  done
  $K get events --sort-by=.lastTimestamp | tail -40 || true
  free -m; df -h / | tail -1
}
trap why EXIT

step "The stores: MySQL, Redis, RabbitMQ and Garage"
for store in mysql redis rabbitmq garage; do
  $K rollout status "statefulset/$store" --timeout=300s
done

step "The Jobs: the database's migrations and Garage's setup"
$K wait --for=condition=complete job/migration-job --timeout=900s
if $K get job garage-init >/dev/null 2>&1; then
  $K wait --for=condition=complete job/garage-init --timeout=600s
fi

step "Every service that runs, ready"
# web-shell waits for a web app, which make web sends, and is not tried
# here; a Deployment the recipe does not run has no replicas.
failed=0
for deploy in $($K get deploy -o jsonpath='{range .items[*]}{.metadata.name}={.spec.replicas}{"\n"}{end}'); do
  name=${deploy%=*}
  [ "${deploy#*=}" = 0 ] && { echo "  $name: not run"; continue; }
  [ "$name" = web-shell ] && { echo "  $name: waits for make web"; continue; }
  if $K rollout status "deploy/$name" --timeout=600s >/dev/null; then
    echo "  $name: ready"
  else
    echo "  $name: NOT READY"; failed=1
    $K logs "deploy/$name" --tail=30 || true
  fi
done
[ "$failed" = 0 ] || { $K get pods; exit 1; }

step "NodeInfo: the release, and what the site offers"
version=$(sed -n 's/^ *newTag: v//p' k8s/kustomization.yml | head -1)
for i in $(seq 1 30); do
  curl -skf --resolve "api.$domain:443:127.0.0.1" "https://api.$domain/nodeinfo/2.1" > nodeinfo.json && break
  sleep 5
done
python3 - "$version" k8s/instance.json nodeinfo.json <<'PY'
import json, os, sys
version, instance_path, nodeinfo_path = sys.argv[1:]
info = json.load(open(nodeinfo_path))
said = info["software"]["version"]
offers = info["metadata"].get("offers") or {}
print(f"  runs {said}, offers {offers}")
problems = []
if said != version:
    problems.append(f"runs {said}, not {version}")
if os.path.exists(instance_path):
    posts, profiles = set(offers.get("posts", [])), set(offers.get("profiles", []))
    for each in json.load(open(instance_path)):
        service, kinds = each["service"], each.get("node_types")
        if each.get("enabled") is False:
            kinds = []
        if kinds is None:
            continue
        kinds = set(kinds) - {"reply"}
        if service == "actor-service":
            if profiles - kinds - {"person"} or kinds - profiles:
                problems.append(f"profiles {sorted(profiles)}, instance.json {sorted(kinds)}")
        else:
            mine = {"text-service": {"note", "article", "topic"}, "photo-service": {"photo"},
                    "video-service": {"video", "audio"}}.get(service, set())
            offered = posts & mine
            # A kind may be listed and still not offered where no profile
            # may write it, or a setting turns it off (VIDEO_UPLOADS).
            if offered - kinds:
                problems.append(f"{service} offers {sorted(offered)}, instance.json {sorted(kinds)}")
for p in problems:
    print("  FAILED:", p)
sys.exit(1 if problems else 0)
PY

echo
echo "$recipe: from make init to a running site, every service ready."
