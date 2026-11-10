# Anahita Recipes

A site ready to run, for each purpose.

[Anahita](https://www.anahita.io) is open-source social software for
communities that want a place of their own, on the fediverse and the
Atmosphere. A recipe is a folder you copy: the choices made and explained,
and the steps from an empty server to the first person signed in. You need
no knowledge of Kubernetes to follow one.

## Choose a recipe

| Recipe | For | Like |
| --- | --- | --- |
| [**commons**](commons) | A social network with everything: notes, photos, videos, articles, groups and events. The one to begin with | Mastodon and Pixelfed, but more |
| [**coffeehouse**](coffeehouse) | Short posts and the conversation around them: notes and photos | Mastodon, Bluesky |
| [**journal**](journal) | Long writing: articles, with notes and photos beside them | WordPress, Medium |
| [**theatre**](theatre) | Video and sound: lectures, music, a channel of your own | YouTube, PeerTube |
| [**gathering**](gathering) | Meetups and events, with groups to host them | Meetup, Luma |
| [**php-migration**](php-migration) | Moving an Anahita PHP site into a new commons site | |

Whether a site is open to anybody or for its members only, as a school or
a company may need, is a choice inside any recipe.

## How it goes

1. **Copy the recipe's folder** somewhere of your own: it is your site.
2. **`make init`** asks for your domain and your email, and makes the keys.
3. **`make server`** prepares a server, and **`make apply`** starts the site.
4. **`make web`** puts the web app live, and you sign in.

Each recipe's README walks through it, and says what it chose and why.

## Only what your site needs

Anahita is small services, each doing one thing. A recipe runs only what
its site offers, and says what that is in one file, `instance.json`. Here
is all of Anahita, as `commons` runs it; the dashed services are the ones a
recipe can leave out.

![Everything Anahita runs, on one server running k3s, as commons runs it.
Thirteen services always run, with three shared over gRPC; eight others,
dashed, run only if the site offers what they bring: videos and sound, the
fediverse, Bluesky and the Atmosphere, websites' feeds, cards for links,
who to follow, downloads and imports, and web-shell. MySQL, Redis,
RabbitMQ and Garage keep the data.](commons/images/what-runs.svg)

## Where to run one

A server with 2 CPUs, 4 GB of memory and 40 GB of disk is enough to begin;
`theatre` asks for more, for its videos. The recipes are written for Amazon
Web Services, OVHcloud and Hetzner: [docs/providers.md](docs/providers.md)
says which have been tried, and others that should work.

**New, and not yet tried from start to finish.** If you try one, tell us
how it went in an [issue](https://github.com/anahitasocial/anahita-recipes/issues).

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
