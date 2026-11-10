# coffeehouse

Short posts and the conversation around them: people and their notes, and
nothing else (the user, 2026-11-09). No groups, events or websites, no
articles, topics or photo posts, and no videos, GIFs or sound. For a town, a club or a field that wants to
talk, not publish, with federation on ActivityPub and AT Protocol, so that
people on Mastodon, Pixelfed, Bluesky and the rest of the Atmosphere can
follow and reply. Named after the coffeehouses of the seventeenth and
eighteenth centuries, called penny universities: for the price of a
coffee, anybody could sit down and argue about the news.

**Not tried yet from start to finish.** It is `commons` with less in it,
and `commons` comes from banu.io, but this recipe has not yet made a site
of its own. If you try it, tell us how it went in an
[issue](https://github.com/anahitasocial/anahita-recipes/issues).

## Contents

1. [What it chooses](#what-it-chooses)
2. [Three things to decide first](#three-things-to-decide-first)
3. [What you need](#what-you-need)
4. [From an empty server to the first person signed in](#from-an-empty-server-to-the-first-person-signed-in)
5. [Running it](#running-it)
6. [Upgrading](#upgrading)
7. [Backups](#backups)
8. [Files at a provider instead of Garage](#files-at-a-provider-instead-of-garage)

## What it chooses

Every choice is in [k8s/config.env](k8s/config.env), with a line saying
why, and what the site offers is in [k8s/instance.json](k8s/instance.json).
Once copied, they are yours to change; `make apply` puts a change in
place.

| Setting | coffeehouse chooses | Why |
| --- | --- | --- |
| `instance.json` | People; notes | What a coffeehouse is for. Groups, events, websites, articles, topics and photo posts are in no menu, composer or tab, and the services refuse them |
| `REGISTRATION_MODE` | `approval` | Anybody may ask to join, and an administrator says yes, so that a new site is not filled by strangers before its rules are written |
| `SITE_READ_ACCESS` | `public` | What is public may be read by anybody, as on Mastodon |
| `FEDERATION_PROTOCOLS` | `activitypub,atproto` | Both networks. Each profile still chooses whether it federates |
| `VIDEO_UPLOADS`, `AUDIO_UPLOADS` | `off` | No videos, GIFs or sound, said here as well as in `instance.json` |
| `FILE_SWEEP` | `on` | Stored files that nothing names any more are removed every night |
| Files | Garage, on the server | No other account needed |

It runs what it offers, with MySQL, Redis, RabbitMQ and Garage on the same
server, at the version named in [k8s/kustomization.yml](k8s/kustomization.yml).

![One server running k3s. Traefik takes every request and hands it to the
gateway, or to web-shell for the web app. Thirteen services always run,
with three shared over gRPC; five others, dashed, run because a
coffeehouse offers what they bring. Video and websites' feeds are not run.
MySQL, Redis, RabbitMQ and Garage keep the data, and four jobs run by the
clock or once.](images/what-runs.svg)

Anahita is small services, each doing one thing, so a site runs only what
it offers. A coffeehouse does not run video-service, video-worker,
syndication-service or syndication-worker: [k8s/not-run.yml](k8s/not-run.yml)
gives them no replicas, so they use no memory, and their addresses stay
for the gateway. To offer one again, take it out of that file, add its kinds
to `instance.json`, and turn its setting on.

<!-- what-runs:start -->

**What each service does,** of those it runs:

| Service | What it does |
| --- | --- |
| `web-shell` | Serves the web app, each page with its own title and picture, so that a shared link shows as itself. |
| `auth-service` | Signing in and signing up, and the accounts people sign in with. |
| `actor-service` | Every kind of profile it offers: people. |
| `text-service` | Notes, and the replies to any post. |
| `photo-service` | Photo posts, which a coffeehouse does not offer: it runs, and takes none. |
| `feed-service` | The chronological feed, reposts, and the custom feeds people make. |
| `socialgraph-service` | Who follows, blocks, mutes and subscribes to whom. |
| `like-service` | Likes. |
| `notification-service` | Notifications in the app. |
| `search-service` | Search for people, posts and shared feeds. |
| `hashtag-service` | Hashtags. |
| `location-service` | The locations posts are tagged with, and finding them on a map. |
| `identity-image-service` | Profile and cover photos, made afresh at each size. |
| `abuse-report-service` | Reports of people and posts, and the cases administrators decide. |
| `graph-grpc-service` | The graph every other service reads: profiles and posts are its nodes, and the ties between them its edges. |
| `file-grpc-service` | Files, in Garage or any S3-compatible store. |
| `mail-grpc-service` | Email, over SMTP. |
| `activitypub-service` | Makes the site a server of the fediverse, for the people who choose to be found there. |
| `atproto-service` | Bluesky and the rest of the Atmosphere: following profiles there, and posting there for whoever connects their own account. |
| `link-preview-service` | The card under a note that links to a page: its title and picture. |
| `recommendation-service` | Recommendations of who to follow. |
| `import-export-service`, `import-export-worker` | A copy of one's own data to download, and a social graph brought in from elsewhere; import-export-worker does each. |

<!-- what-runs:end -->

## Three things to decide first

Before the first person joins:

- **Who may join.** `approval`, as chosen; `invite`, only those an
  administrator invites; `open`, anybody; `closed`, nobody.
- **Who may read.** `public`, as chosen; `registered` for a site for its
  members only, as a school or a company may need.
- **Your terms.** The web app comes with a Terms of Service and a Privacy
  Policy to begin from, which are not legal advice. Put your own in
  `web/legal/` (`tos.md`, `privacy.md`, and anahita-web's
  `src/statics/legal/index.js` with their versions) and `make web`.

## What you need

1. **A domain,** and access to its DNS records.
2. **A mail provider** that sends over SMTP: its server, port, user name
   and password. Without mail, nobody can be sent the code to sign in.
3. **A server:** Ubuntu 24.04 with 2 CPUs, 4 GB of memory and 40 GB of
   disk. [deploy/README.md](deploy/README.md) makes one at AWS, Hetzner or
   OVHcloud.
4. **On your own computer:** `git`, `make`, `ssh` with a key, `kubectl`,
   `openssl` and `perl`; Node and `yarn` to build the web app; and the AWS
   CLI to upload it (it speaks to Garage too, and needs no AWS account).

## From an empty server to the first person signed in

Copy this folder, `coffeehouse/`, somewhere of your own: it is the whole site.
Keep it in a private git repository if you like; `k8s/secrets.env` is never
committed.

1. **Make the server** ([deploy/README.md](deploy/README.md)), and note its
   address and the user to sign in as.
2. **Point the five names at it:** your domain, and its `www.`, `api.`,
   `auth.` and `files.` ([deploy/README.md](deploy/README.md#the-five-names)).
3. **`make init`.** It asks for the domain, the site's name, your email,
   the mail provider and the server, puts the domain in every file, and
   makes every password and key into `k8s/secrets.env`. **Keep a copy of
   that file somewhere safe:** without its `CRYPT_LOCAL_KEY` nobody can sign
   in.
4. **`make server`.** Over SSH: a swap file, k3s, and cert-manager, which
   gets the certificates. It brings the server's kubeconfig to
   `~/.kube/<domain>.yaml`.
5. **`make tunnel`,** in a terminal of its own, left open. Kubernetes is
   reached through SSH, never over the internet.
6. **`make apply`.** The first time takes some minutes, while the images
   are fetched. `make status` shows the pods: every one `Running`, and
   `migration-job` and `garage-init` `Completed`, but for `web-shell`,
   which waits, failing to start, until there is a web app to send: the
   next step.
7. **`make web`.** Builds the web app with your site's name and puts it
   live. Your site is now at `https://<domain>`.
8. **Sign in.** The first super administrator, your email, is sent a link
   to set a password. If the mail has not arrived, the link is in
   auth-service's log: `make logs SERVICE=auth-service`.
9. **Try it:** make a post, and ask somebody to join. As an administrator,
   you approve them.

## Running it

| Task | What it does |
| --- | --- |
| `make` | Lists every task |
| `make tunnel` | Opens the way to the cluster; the tasks below need it |
| `make status` | The pods, and how much of the server is in use |
| `make logs SERVICE=auth-service` | The last hour of a service's log |
| `make restart SERVICE=web-shell` | Starts a service again |
| `make apply` | Puts a change to `k8s/` in place |
| `make web` | Builds the web app again and puts it live; `REF=` for another version of anahita-web |
| `make backup` | Copies the database into the files now |
| `make mail-off` | Stops every email at once; `make mail-on` sends again |

A logo of your own goes in `web/brand/` (`logo-512.png`, and the others
`web/build.sh` names), a theme in `web/theme/` (anahita-web's
`docs/customising.md`); then `make web`.

## Upgrading

```sh
make upgrade v1.2.4
make apply
```

`make upgrade` changes the version on every line of
`k8s/kustomization.yml`, and names the release's notes: read what it needs
before `make apply`. The database is upgraded as the new version starts.

## Backups

1. **The database** is copied every night at 03:30 UTC into the site's
   files, under `backups/mysql/`; `make backup` does it at once.
   anahita-services' `docs/deploying.md`, under "Database, Redis and
   RabbitMQ", says how to restore one.
2. **The whole server:** AWS keeps a snapshot of the disk every day, for
   seven days (`deploy/aws/`). At Hetzner and OVHcloud, turn on their
   backups; the database's copies are on the same disk as the database
   until you do.
3. **`k8s/secrets.env`:** a copy somewhere other than the server and this
   computer.

## Files at a provider instead of Garage

A provider's S3-compatible store (AWS S3, OVHcloud's, Cloudflare's R2) can
keep the files in place of Garage, on a new site, before anybody posts:

1. In `k8s/kustomization.yml`, remove the `garage` component.
2. In `k8s/ingress.yml`, remove the `garage` Ingress, and the `files.`
   name from your DNS.
3. In `k8s/config.env`, give the store's `STORAGE_ENDPOINT` (empty for AWS
   S3), `STORAGE_REGION` and `STORAGE_BUCKET`, and remove
   `STORAGE_PUBLIC_ENDPOINT` and `STORAGE_PATH_STYLE` unless the store asks
   for them; in `k8s/secrets.env`, its key in `STORAGE_ACCESS_KEY` and
   `STORAGE_SECRET_KEY`.
4. In `k8s/web-shell.yml` and `web/publish.sh`, the store's address in place
   of Garage's.

anahita-services' `docs/configuration.md`, under "Storage", describes each
setting.
