<img src="docs/images/ramen.svg" alt="A bowl of ramen" width="120" align="right">
<img src="docs/images/anahita-logo.svg" alt="Anahita" width="33%">

# Anahita Recipes

A site ready to run, for each purpose.

[Anahita](https://www.anahita.io) is open-source social software for
communities that want a place of their own, on the fediverse and the
Atmosphere. A recipe is a folder you copy: the choices made and explained,
and the steps from an empty server to the first person signed in. You need
no knowledge of Kubernetes to follow one.

## Choose a recipe

Their names are French, as recipes' often are, and as Canada, where
Anahita is made, speaks it beside English.

| Recipe | What it is |
| --- | --- |
| [**classique**](classique) | A social network with everything Anahita does: notes, photos, videos and articles; groups, events and channels. The one to begin with when you are not sure |
| [**café**](cafe) | Short posts and the conversation around them: people sharing notes and photos with those who follow them, for a town, a club or a field that wants to talk, not publish |
| [**journal**](journal) | Long writing under each writer's own name: articles with their covers, and notes and photos beside them, for writers and the people who follow them |
| [**galerie**](galerie) | Photos first: each person's photo posts, a series in one, and the conversation under them, for photographers, a camera club or an art school |
| [**vidéothèque**](videotheque) | Video and sound, each person's own: lectures, concerts, music and talks of up to an hour, and the replies under them |
| [**rendez-vous**](rendez-vous) | Meetups and events: groups that organise them, who is going, and notes, photos and topics around them. Nothing is sold: there are no tickets |
| [**forum**](forum) | Discussions that last: groups as boards, topics in them and the replies under them, where an old answer is found as easily as a new one |
| [**quartier**](quartier) | A neighbourhood online, run by its own people: each local shop, business and facility has a channel for its news, photos, videos and events, and one neighbourhood's site follows the next |
| [**php-migration**](php-migration) | Moving an Anahita PHP site into a new classique site |

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
its site offers, and says what that is in one file, `instance.json`. Each
recipe's README draws what it runs.

## Where to run one

A server with 2 CPUs, 4 GB of memory and 40 GB of disk is enough to begin;
`videotheque` asks for more, for its videos. The recipes are written for Amazon
Web Services, OVHcloud and Hetzner: [docs/providers.md](docs/providers.md)
says which have been tried, and others that should work.

**Tried on every change.** [smoke.sh](smoke.sh) takes each recipe from
`make init` to a running site, on a GitHub runner as its server, every
service ready and offering what the recipe says; once a week too. A domain
of its own, Let's Encrypt, mail and `make web` are not tried there. If you
run one, tell us how it went in an
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
