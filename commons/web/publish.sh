#!/bin/sh
# make publish: puts web/build/ live. Uploads it to the site's files, in
# Garage, as a folder of its own, web/<build>/, names it in web/current,
# then starts web-shell again, whose first step copies the build named there
# (k8s/web-shell.yml). The build before stays, so going back is web/current
# set to it, and make restart SERVICE=web-shell.
#
# Garage is reached at https://files.<domain>, with the site's own key from
# k8s/secrets.env, so the server must be up and its names in place. Needs
# the AWS CLI, which speaks to any S3 store, Garage among them.
#
#   web/publish.sh <kubeconfig> <context>
set -eu
KUBECONFIG_FILE=${1:?the kubeconfig of the site}
CONTEXT=${2:?its context}
HERE=$(cd "$(dirname "$0")" && pwd)
SITE=$(cd "$HERE/.." && pwd)
value() { sed -n "s/^$1=//p" "$2" | head -1; }
DOMAIN=$(value DOMAIN "$SITE/site.env")
BUCKET=$(value STORAGE_BUCKET "$SITE/k8s/config.env")
test -f "$HERE/build/index.html" || { echo "No build: run make build first." >&2; exit 1; }
command -v aws >/dev/null || { echo "The AWS CLI is needed to upload the build." >&2; exit 1; }
KUBECTL="kubectl --kubeconfig $KUBECONFIG_FILE --context $CONTEXT"
$KUBECTL -n anahita get deployment/web-shell >/dev/null 2>&1 || {
  echo "The cluster does not answer: open the tunnel (make tunnel) first." >&2; exit 1; }

# Garage, as an S3 store: its address, the site's key, and paths with the
# bucket in them, never as a name of its own. Nothing of yours in ~/.aws
# is read or changed.
CONFIG=$(mktemp)
trap 'rm -f "$CONFIG"' EXIT
printf '[default]\ns3 =\n  addressing_style = path\n' > "$CONFIG"
export AWS_CONFIG_FILE="$CONFIG" AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_DEFAULT_REGION=garage
AWS_ACCESS_KEY_ID=$(value STORAGE_ACCESS_KEY "$SITE/k8s/secrets.env")
AWS_SECRET_ACCESS_KEY=$(value STORAGE_SECRET_KEY "$SITE/k8s/secrets.env")
export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
s3() { aws --endpoint-url "https://files.$DOMAIN" s3 "$@"; }

build="$(date -u +%Y%m%d-%H%M%S)-$(cat "$HERE/build/.anahita-web" 2>/dev/null || echo unknown)"
echo "Uploading the web app as web/$build/"
s3 sync "$HERE/build/" "s3://$BUCKET/web/$build/" --only-show-errors --exclude ".anahita-web"
printf '%s\n' "$build" | s3 cp - "s3://$BUCKET/web/current" --only-show-errors

$KUBECTL -n anahita rollout restart deployment/web-shell
$KUBECTL -n anahita rollout status deployment/web-shell --timeout=180s
echo "https://$DOMAIN sends build $build"
