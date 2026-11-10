#!/bin/sh
# make build: builds the web app for this site, into web/build/.
#
# anahita-web is fetched from GitHub at REF (main unless said), into a
# folder of its own, so that nothing else gets into the build. The site's
# name and description are config.env's, and the API's address follows from
# the domain in site.env. What is in web/ is put in, when it is there:
#
#   web/theme/   a theme of your own (anahita-web's docs/customising.md,
#                Themes): a copy of src/assets/default, changed
#   web/legal/   your Terms of Service and Privacy Policy, in place of
#                anahita-web's starting ones (tos.md, privacy.md, index.js)
#   web/brand/   your logo and icons: logo-512.png, and if you have them,
#                favicon.ico, logo-32.png, logo-180.png, logo-192.png and
#                og.jpg, the picture of a shared link (1200 by 630)
#
# Needs git, Node and yarn.
#
#   web/build.sh [ref]
set -eu
REF=${1:-main}
HERE=$(cd "$(dirname "$0")" && pwd)
SITE=$(cd "$HERE/.." && pwd)
value() { sed -n "s/^$1=//p" "$2" | head -1; }
DOMAIN=$(value DOMAIN "$SITE/site.env" 2>/dev/null || true)
: "${DOMAIN:?no DOMAIN in site.env: run make init first}"
NAME=$(value SITE_NAME "$SITE/k8s/config.env")
DESCRIPTION=$(value ANAHITA_INSTANCE_DESCRIPTION "$SITE/k8s/config.env")
API=${API:-https://api.$DOMAIN}
for tool in git node yarn; do
  command -v $tool >/dev/null || { echo "$tool is needed to build the web app." >&2; exit 1; }
done

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
git clone --quiet --filter=blob:none https://github.com/anahitasocial/anahita-web.git "$WORK/web"
git -C "$WORK/web" checkout --quiet --detach "$REF"
COMMIT=$(git -C "$WORK/web" rev-parse --short HEAD)
echo "anahita-web at $COMMIT, for $API"

ASSETS=default
if [ -f "$HERE/theme/index.js" ]; then
  cp -R "$HERE/theme" "$WORK/web/src/assets/site"
  ASSETS=site
  echo "with the theme in web/theme/"
fi
if [ -f "$HERE/legal/tos.md" ]; then
  cp "$HERE"/legal/* "$WORK/web/src/statics/legal/"
  echo "with the terms in web/legal/"
fi

cd "$WORK/web"
yarn install --frozen-lockfile --silent
env -i PATH="$PATH" HOME="$HOME" \
  REACT_APP_ASSETS="$ASSETS" \
  REACT_APP_NAME="$NAME" \
  REACT_APP_DESCRIPTION="$DESCRIPTION" \
  REACT_APP_API_BASE_URL="$API" \
  ${LANGUAGE:+REACT_APP_LANGUAGE="$LANGUAGE"} \
  GENERATE_SOURCEMAP=false \
  yarn -s build

rm -rf "$HERE/build"
cp -R build "$HERE/build"
OUT=$HERE/build
# The logo at a fixed address, for SITE_LOGO_URL (https://<domain>/logo.png):
# the sign-in pages, every email, the home page and the menu. Anahita's
# mark when web/brand/ has none.
if [ -f "$HERE/brand/logo-512.png" ]; then
  cp "$HERE/brand/logo-512.png" "$OUT/logo.png"
  cp "$HERE/brand/logo-512.png" "$OUT/icon-512.png"
  for size in 32 180 192; do
    [ -f "$HERE/brand/logo-$size.png" ] && cp "$HERE/brand/logo-$size.png" "$OUT/icon-$size.png"
  done
  [ -f "$HERE/brand/favicon.ico" ] && cp "$HERE/brand/favicon.ico" "$OUT/favicon.ico"
  echo "with the logo in web/brand/"
else
  cp "$OUT/icon-512.png" "$OUT/logo.png"
fi
[ -f "$HERE/brand/og.jpg" ] && cp "$HERE/brand/og.jpg" "$OUT/statics/media/ogimage.jpg"
# The installed app's name, the site's.
NAME="$NAME" perl -pi -e 's/("(short_)?name": )"[^"]*"/$1"$ENV{NAME}"/' "$OUT/manifest.json"
# What this build is, for web/publish.sh to name it by.
echo "$COMMIT" > "$OUT/.anahita-web"
echo "Built into web/build/."
