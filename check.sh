#!/bin/sh
# Checks every recipe, needing no cluster:
#
#   1. It builds: kubectl kustomize on its k8s/, with the example secrets.
#   2. Every setting it names exists, in anahita-services'
#      docs/configuration.md at the version the recipe runs, or on main.
#   3. What the recipes share is the same in each as in commons: the
#      Makefile, scripts/, deploy/, and web/'s two scripts.
#
#   ./check.sh
set -eu
cd "$(dirname "$0")"
SHARED="Makefile scripts deploy web/build.sh web/publish.sh"
failed=0
fail() { echo "  FAILED: $*"; failed=1; }

for recipe in */; do
  recipe=${recipe%/}
  [ -f "$recipe/k8s/kustomization.yml" ] || continue
  echo "$recipe"

  # 1. It builds. The example secrets in place of the real ones, which are
  # never here, and taken away after.
  secrets="$recipe/k8s/secrets.env"
  if [ -e "$secrets" ]; then fail "$secrets is here: it must never be committed"; continue; fi
  cp "$recipe/k8s/secrets.env.example" "$secrets"
  if kubectl kustomize "$recipe/k8s" > /dev/null 2> "$recipe/k8s/.check.err"; then
    echo "  builds"
  else
    fail "kubectl kustomize: $(head -3 "$recipe/k8s/.check.err")"
  fi
  rm -f "$secrets" "$recipe/k8s/.check.err"

  # 2. Every setting exists, at the version the recipe runs. A setting
  # documented only after that release, on main, counts too: the docs may
  # be better than they were.
  version=$(sed -n 's/^ *newTag: //p' "$recipe/k8s/kustomization.yml" | head -1)
  raw=https://raw.githubusercontent.com/anahitasocial/anahita-services
  docs=$(curl -sfL "$raw/$version/docs/configuration.md" && curl -sfL "$raw/main/docs/configuration.md") \
    || { fail "configuration.md at $version or on main could not be fetched"; docs=""; }
  if [ -n "$docs" ]; then
    missing=""
    for key in $(grep -hoE '^[A-Z][A-Z0-9_]+' "$recipe/k8s/config.env" "$recipe/k8s/secrets.env.example" | sort -u); do
      printf '%s' "$docs" | grep -q "\b$key\b" || missing="$missing $key"
    done
    if [ -n "$missing" ]; then fail "not in configuration.md at $version nor on main:$missing"; else echo "  every setting is in configuration.md"; fi
  fi

  # 3. The shared files, the same as commons'.
  if [ "$recipe" != commons ]; then
    for path in $SHARED; do
      diff -rq "commons/$path" "$recipe/$path" > /dev/null 2>&1 || fail "$path differs from commons'"
    done
  fi
done

# The migration's script compiles.
for script in */migration/*.py; do
  [ -f "$script" ] || continue
  python3 -m py_compile "$script" 2>/dev/null && echo "$script compiles" || fail "$script does not compile"
done
find . -name __pycache__ -type d -prune -exec rm -r {} +

[ "$failed" = 0 ] && echo "Every recipe checked." || { echo "Some checks failed."; exit 1; }
