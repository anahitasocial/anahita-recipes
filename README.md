# Anahita Recipes

A site ready to run, for each purpose.

[Anahita](https://www.anahita.io) is an open-source social network for the
fediverse, built as a set of small services. The hardest part of running it
is not Anahita: it is Kubernetes and the knowledge of running servers around
it. A recipe writes that knowledge down once. Each is a directory you copy:
the configuration chosen and explained, a Makefile in which every task is
one word (`make apply`, `make status`, `make logs`), and the steps from an
empty server to the first person signed in.

What a site does not need is not run, and what it needs more of is given
more. That is what small services are for.

**`commons`, `coffeehouse` and `php-migration` are ready to try;** the others are planned.
Nobody has tried them from start to finish yet: if you do, tell us how it
went, in an [issue](https://github.com/anahitasocial/anahita-recipes/issues).

## The recipes

| Recipe | For | Like | State |
| --- | --- | --- | --- |
| [`commons`](#commons) | A classic social network | Mastodon and Pixelfed, but more | Ready to try |
| [`coffeehouse`](#coffeehouse) | Microblogging | Mastodon, Bluesky | Ready to try |
| [`journal`](#journal) | Long-form content | WordPress, Medium | Planned |
| [`theatre`](#theatre) | Video sharing: arts, music, news, lectures | YouTube, PeerTube | Planned |
| [`gathering`](#gathering) | Organising meetups and events | Meetup, Luma | Planned |
| [`php-migration`](#php-migration) | Migrating an Anahita PHP site, relaunched as a Commons site | | Ready to try |

Whether a site is open to anybody or for its members only, as a school or a
company may need, is a choice inside any recipe.

### commons

Everything, for everyone. Notes, photos, video and articles; groups and
their followers; events and their hosts; locations on posts; and federation
with both ActivityPub and AT Protocol, so that people on Mastodon, Pixelfed
and Bluesky can follow and reply. It is Anahita as a whole, and the one to
begin with if you are not sure which you need. A commons is what a
community holds together and nobody owns.

### coffeehouse

Short posts and the conversation around them: notes and photos, and
nothing else. Articles, topics, events and websites are turned off, and
there are no videos, GIFs or sound, so the video services are not run. For
a town, a club or a field that wants to talk, not publish. Named after the
coffeehouses of the seventeenth and eighteenth centuries, called penny
universities: for the price of a coffee, anybody could sit down and argue
about the news.

### journal

Articles first, for newsrooms, research groups, libraries and writers. The
home page is a list of article cards with their covers, and short notes sit
beside them for what does not need an article. A journal is written over
time and kept, and old and useful articles are found as easily as new ones.

### theatre

Video first, for a school's lectures, a festival or a channel of one's own
that nobody else controls. The home page is a grid of thumbnails, uploads
may be larger, and the service that prepares video is given more of the
server.

### gathering

What is on, first. Events lead, and groups are their organisers: for a
library's programme, a community centre or a network of local chapters.
People see what is coming, say they are going and follow the groups that
run them. Nothing is sold: there are no tickets.

### php-migration

Moving a site from Anahita PHP to today's Anahita, the way banu.io was
moved. It holds the move alone. First make the new site with
[`commons`](#commons), following its README as far as `make apply`; then
this recipe moves the old site into it. Each step is one `make` task, and
each that changes anything first shows what it would change, with nothing
changed:

1. Archive the old site, and prove the archive opens.
2. Load its database into the new site's, and upgrade it. The old site is
   only read, so this can be done again from the archive until it is right.
3. Copy its files into the new site's.
4. Check that people, posts and files are all there.
5. Retire the old site.

A site that has run for years carries what nobody needs any more. The
recipe comes with examples of thinning it, from what was done for banu.io,
to change for your own site. Each, like the steps above, first counts what
it would change, and with `-apply` keeps a copy of everything it removes
before removing it:

1. **Inactive accounts:** the people who have not signed in since a date,
   and wrote nothing, removed with everything they own; a list of those to
   keep whatever their last visit.
2. **Old posts:** notes, replies, articles or topics older than a date,
   removed with their threads; photos kept, whatever their age.
3. **Posts with nobody behind them:** those whose author was deleted long
   ago, and so are shown to nobody.
4. **Photos moved to another profile:** a person's photos out of a group,
   or from one profile to another, with their files, which are kept under
   their owner's folder and must move too.
5. **Groups:** those nobody posts in, removed with what is in them, once
   whatever is to be kept is moved out.
6. **Files nothing names:** removed after the rest, by the nightly sweep.

## What a recipe is made of

Every recipe is laid out the same way, so that once you know one, you know
where to look in all of them:

```
commons/
  README.md             who it is for, what it decides, and the steps from
                        an empty server to the first person signed in
  Makefile              every task one word; `make` lists them
  scripts/              what make init and make server run
  k8s/
    kustomization.yml   Anahita's services at a version, and your site's names
    config.env          the settings, each with a line saying why
    secrets.env.example
    patches/            the services it leaves out, and how to put one back
  deploy/               the server and its DNS: aws/, ovhcloud/, hetzner/
  web/                  the theme, and the scripts that build and publish it
```

A recipe is a start, not a lock: once copied, its settings are yours to
change.

## Where to run one

One server with 2 CPUs, 4 GB of memory and 40 GB of disk is enough to
begin. Recipes are written for Amazon Web Services, OVHcloud and Hetzner;
[docs/providers.md](docs/providers.md) says which have been tried, and lists
other providers in Canada and Europe that should work. If you try one, tell
us how it went in an
[issue](https://github.com/anahitasocial/anahita-recipes/issues).

## More

| To learn | Read |
| --- | --- |
| What Anahita is | [www.anahita.io](https://www.anahita.io) |
| The services, their settings and the API | [anahita-services](https://github.com/anahitasocial/anahita-services) |
| The web app | [anahita-web](https://github.com/anahitasocial/anahita-web) |
| How the recipes are planned | [recipes.md](https://github.com/anahitasocial/anahita-services/blob/main/docs/plans/recipes.md) |

Anahita was founded by Rastin Mehr, and is maintained and developed by
[rmd Studio](https://www.rmdstudio.com). The recipes are under the MIT
licence ([LICENSE](LICENSE)).
