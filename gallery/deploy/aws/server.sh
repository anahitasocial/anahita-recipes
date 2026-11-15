#!/bin/sh
# Deploys the site's server on AWS (deploy/aws/server.yaml). Run it again to
# change something: the server is never replaced, since the image it was
# made from is kept from the first run.
#
#   AWS_PROFILE=<profile> deploy/aws/server.sh <domain> <key pair name>
#   AWS_PROFILE=<profile> HOSTED_ZONE_ID=<zone> deploy/aws/server.sh <domain> <key pair name>
#
# REGION is ca-central-1 unless said. Nothing falls back to a default
# profile, so it cannot reach an account it was not pointed at.
set -eu
: "${AWS_PROFILE:?name the AWS profile}"
export AWS_PROFILE
DOMAIN=${1:?the domain of the site}
KEY=${2:?the name of an EC2 key pair, for SSH}
REGION=${REGION:-ca-central-1}
NAME=$(printf '%s' "$DOMAIN" | tr . -)
STACK=$NAME-server
cd "$(dirname "$0")"

echo "Account $(aws sts get-caller-identity --query Account --output text), $REGION"

# A first deploy that failed leaves an empty stack that cannot be deployed
# over: it holds nothing, so it is deleted and the deploy starts afresh.
status=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo NONE)
if [ "$status" = ROLLBACK_COMPLETE ]; then
  aws cloudformation delete-stack --region "$REGION" --stack-name "$STACK"
  aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$STACK"
  status=NONE
fi

overrides="Name=$NAME DomainName=$DOMAIN KeyName=$KEY"
if [ "$status" = NONE ]; then
  image=$(aws ssm get-parameter --region "$REGION" \
    --name /aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id \
    --query Parameter.Value --output text)
  vpc=$(aws ec2 describe-vpcs --region "$REGION" --filters Name=isDefault,Values=true \
    --query 'Vpcs[0].VpcId' --output text)
  echo "First deploy: $image in $vpc"
  overrides="$overrides ImageId=$image VpcId=$vpc"
fi
[ -n "${HOSTED_ZONE_ID:-}" ] && overrides="$overrides HostedZoneId=$HOSTED_ZONE_ID"
[ -n "${SSH_FROM:-}" ] && overrides="$overrides SshFrom=$SSH_FROM"

# shellcheck disable=SC2086
aws cloudformation deploy --region "$REGION" --stack-name "$STACK" \
  --template-file server.yaml --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset --parameter-overrides $overrides

address=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='Address'].OutputValue" --output text)
echo "The server is at $address; sign in as ubuntu. Next: make init."
