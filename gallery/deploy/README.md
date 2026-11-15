# Making the server

A recipe runs on one Ubuntu 24.04 server with 2 CPUs, 4 GB of memory and
40 GB of disk, open to the internet on ports 22, 80 and 443 alone. Make it
at a provider, point the site's names at it, then go on with `make init`
and `make server`, which are the same everywhere.

| Provider | How | State |
| --- | --- | --- |
| [AWS](#aws) | `aws/server.sh`, from a CloudFormation template | The way banu.io's server was made, with Ubuntu in place of Amazon Linux; this template not tried yet |
| [Hetzner](#hetzner) | `hetzner/server.sh`, with its `hcloud` CLI | Not tried yet |
| [OVHcloud](ovhcloud/README.md) | In its control panel, step by step | Not tried yet |

Other providers that should work are in
[docs/providers.md](../../docs/providers.md). Any will do that gives you
such a server, with your SSH key on it, and a firewall.

## The five names

Each points to the server's address, with an A record at your domain's DNS
provider:

| Name | For |
| --- | --- |
| `example.org` | The web app |
| `www.example.org` | Sent on to `example.org` |
| `api.example.org` | The API |
| `auth.example.org` | Signing in |
| `files.example.org` | Photos, videos and other files |

Make them before `make apply`: the certificates are given only to names
that already lead to the server.

## AWS

Needs the AWS CLI, a profile for your account, and an EC2 key pair in the
region (EC2 › Key pairs; import your own public key). Then:

~~~sh
AWS_PROFILE=<profile> deploy/aws/server.sh <domain> <key pair name>
~~~

It makes a t4g.medium in `ca-central-1` (`REGION=` for another), a firewall,
an address that stays the same, and a snapshot of the disk every day, kept
seven days. With `HOSTED_ZONE_ID=<zone>` it also makes the five names in
Route 53. `SSH_FROM=<your address>/32` lets SSH in from your address alone.
The user to sign in as is **ubuntu**.

## Hetzner

Needs [hcloud](https://github.com/hetznercloud/cli), with a context for your
project (`hcloud context create <name>`, with an API token from the Cloud
Console). Then:

~~~sh
deploy/hetzner/server.sh <domain>
~~~

It makes a CAX11 (2 ARM vCPU, 4 GB) in Falkenstein (`LOCATION=nbg1` or
`hel1` for Nuremberg or Helsinki), a firewall open to 22, 80 and 443, and
puts `~/.ssh/id_ed25519.pub` on it (name another file after the domain).
`BACKUPS=on` turns on Hetzner's daily backups. The user to sign in as is
**root**.
