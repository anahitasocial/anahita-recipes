#!/bin/sh
# make init: asks for the few things only you know, then puts them in place.
#
#   1. site.env: the domain, the server's address and the user to sign in
#      to it with over SSH, which the Makefile reads.
#   2. k8s/: your domain in place of example.org, in every file.
#   3. k8s/config.env: the site's name, and the addresses mail goes from.
#   4. k8s/secrets.env: every password and key, made here, and your mail
#      provider's sign-in.
#
# It stops, changing nothing, when k8s/secrets.env is there already: the
# keys in it cannot be made again without losing the site's data.
set -eu
cd "$(dirname "$0")/.."

if [ -f k8s/secrets.env ]; then
  echo "k8s/secrets.env is there already, so this site was set up before. Nothing changed." >&2
  exit 1
fi
command -v openssl >/dev/null || { echo "openssl is needed, to make the keys." >&2; exit 1; }

ask() { # ask <question> <default>: the answer, or the default when empty
  if [ -n "$2" ]; then printf '%s [%s]: ' "$1" "$2" >&2; else printf '%s: ' "$1" >&2; fi
  read -r answer
  echo "${answer:-$2}"
}

echo "A few questions. Press Enter to take what is in [brackets]." >&2
echo >&2
DOMAIN=$(ask "The site's domain, without www (example: social.example.ca)" "")
test -n "$DOMAIN" || { echo "A domain is needed." >&2; exit 1; }
NAME=$(ask "The site's name, as people will see it" "$DOMAIN")
ADMIN=$(ask "Your email: the first super administrator, and certificate warnings" "admin@$DOMAIN")
FROM=$(ask "The address the site's email is sent from" "noreply@$DOMAIN")
SUPPORT=$(ask "The address people write to for help" "support@$DOMAIN")
SMTP_HOST=$(ask "Your mail provider's SMTP server" "")
SMTP_PORT=$(ask "Its port: 587, or 465 for TLS from the start" "587")
SMTP_USER=$(ask "The user name to send mail with" "$FROM")
printf 'Its password (not shown): ' >&2
stty -echo 2>/dev/null || true; read -r SMTP_PASSWORD; stty echo 2>/dev/null || true; echo >&2
SERVER=$(ask "The server's address (IPv4), from your provider" "")
SSH_USER=$(ask "The user to sign in to it with over SSH" "root")

SECURE=false; [ "$SMTP_PORT" = 465 ] && SECURE=true
hex() { openssl rand -hex "$1"; }

# 1. site.env
cat > site.env <<END
# Written by make init. The Makefile reads it; nothing in it is secret.
DOMAIN=$DOMAIN
SERVER=$SERVER
SSH_USER=$SSH_USER
END

# 2. The domain, everywhere. www.yml names it as a pattern, with its dots
# escaped, so that form goes first.
ESCAPED=$(printf '%s' "$DOMAIN" | sed 's/\./\\./g')
for f in k8s/*.yml k8s/*.json k8s/config.env; do
  DOMAIN="$DOMAIN" ESCAPED="$ESCAPED" perl -pi -e 's/example\\\.org/$ENV{ESCAPED}/g; s/example\.org/$ENV{DOMAIN}/g' "$f"
done

# 3. config.env: the name and the addresses. | as the separator, since an
# address has no |.
set_config() {
  KEY="$1" VALUE="$2" perl -pi -e 's|^\Q$ENV{KEY}\E=.*|$ENV{KEY}=$ENV{VALUE}|' k8s/config.env
}
set_config SITE_NAME "$NAME"
set_config SUPER_ADMIN_EMAIL "$ADMIN"
set_config GEOCODER_CONTACT "$ADMIN"
set_config SYSTEM_EMAIL "$FROM"
set_config SUPPORT_EMAIL "$SUPPORT"
set_config SMTP_HOST "$SMTP_HOST"
set_config SMTP_PORT "$SMTP_PORT"
set_config SMTP_SECURE "$SECURE"
ADMIN="$ADMIN" perl -pi -e 's|^(\s*email:).*|$1 $ENV{ADMIN}|' k8s/issuer.yml

# 4. secrets.env, from the example, readable by you alone.
MYSQL_PASSWORD=$(hex 16)
RABBITMQ_PASSWORD=$(hex 16)
umask 077
cat > k8s/secrets.env <<END
# Written by make init. Keep a copy somewhere safe, CRYPT_LOCAL_KEY above
# all: without it nobody can sign in. Never commit it.
MYSQL_USER=anahita
MYSQL_PASSWORD=$MYSQL_PASSWORD
MYSQL_ROOT_PASSWORD=$(hex 16)
DSN=anahita:$MYSQL_PASSWORD@(mysql:3306)/anahita?parseTime=true
RABBITMQ_USER=anahita
RABBITMQ_PASSWORD=$RABBITMQ_PASSWORD
AMQP_ADDR=amqp://anahita:$RABBITMQ_PASSWORD@rabbitmq:5672
REDIS_PASSWORD=
SECURE_COOKIE_KEY=$(hex 16)
CRYPT_LOCAL_KEY=$(hex 16)
GARAGE_RPC_SECRET=$(hex 32)
GARAGE_ADMIN_TOKEN=$(openssl rand -base64 32)
STORAGE_ACCESS_KEY=GK$(hex 12)
STORAGE_SECRET_KEY=$(hex 32)
SMTP_USER=$SMTP_USER
SMTP_PASSWORD=$SMTP_PASSWORD
END

echo >&2
echo "Done. Your site is $DOMAIN, on $SERVER." >&2
echo "Keep a copy of k8s/secrets.env somewhere safe. Next: make server." >&2
