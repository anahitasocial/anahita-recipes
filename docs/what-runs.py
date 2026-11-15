#!/usr/bin/env python3
"""Draws each recipe's diagram, <recipe>/images/what-runs.svg: the server,
the services it always runs and what each gives, those it runs because it
offers what they bring (dashed), what keeps the data, what runs by the
clock, and what lies outside. One drawing for every recipe, so that they
never drift apart.

    python3 docs/what-runs.py

A new recipe is a line in RECIPES: which of OPTIONAL it runs.
"""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Run by every recipe, by name, with what each gives, short enough for a
# box. The sentence for each is in commons/README.md, under the diagram.
ALWAYS = [
    ("auth-service", "sign-in, accounts"),
    ("actor-service", "people, groups, events"),
    ("text-service", "notes, articles, topics"),
    ("feed-service", "feeds, reposts"),
    ("socialgraph-service", "follows, blocks, mutes"),
    ("like-service", "likes"),
    ("notification-service", "notifications"),
    ("search-service", "search"),
    ("hashtag-service", "hashtags"),
    ("location-service", "locations, maps"),
    ("identity-image-service", "profile and cover photos"),
    ("abuse-report-service", "reports"),
]
SHARED = [
    ("graph-grpc-service", "the graph"),
    ("file-grpc-service", "files"),
    ("mail-grpc-service", "email"),
]
# Run only where a site offers what they bring: what, and the services.
OPTIONAL = {
    "photos": ("Photo posts", "photo-service"),
    "video": ("Videos, GIFs and sound", "video-service, video-worker"),
    "fediverse": ("The fediverse", "activitypub-service"),
    "atmosphere": ("Bluesky and the Atmosphere", "atproto-service"),
    "websites": ("Websites' feeds", "syndication-service, syndication-worker"),
    "cards": ("Cards for links", "link-preview-service"),
    "follow": ("Who to follow", "recommendation-service"),
    "data": ("Downloads and imports", "import-export-service, import-export-worker"),
}
EVERYTHING = list(OPTIONAL)
SOCIAL = ["fediverse", "atmosphere", "cards", "follow", "data"]
RECIPES = {
    "commons": EVERYTHING,
    "coffeehouse": ["photos"] + SOCIAL,
    "journal": ["photos"] + SOCIAL,
    "theatre": ["video"] + SOCIAL,
    "gathering": ["photos"] + SOCIAL,
    "gallery": ["photos"] + SOCIAL,
    "forum": SOCIAL,
}

# The colours: slate for the frame and the words, one colour for each kind
# of service, so that what goes together is seen together.
INK, SLATE, MUTED, FAINT = "#0F172A", "#334155", "#64748B", "#94A3B8"
PAGE, PANEL, CARD, BORDER = "#F8FAFC", "#EEF2F7", "#FFFFFF", "#E2E8F0"
COLOURS = {
    "posts": "#2563EB",    # profiles and posts
    "people": "#7C3AED",   # between people
    "finding": "#0D9488",  # finding things
    "safety": "#EA580C",   # signing in, and keeping the site safe
    "shared": "#CA8A04",   # shared by the others, over gRPC
    "offered": "#C026D3",  # only if the site offers it
}
LEGEND = [
    (COLOURS["posts"], "profiles and posts"), (COLOURS["people"], "between people"),
    (COLOURS["finding"], "finding things"), (COLOURS["safety"], "signing in, and safety"),
    (COLOURS["shared"], "shared, over gRPC"), ("dashed", "only if the site offers it"),
]
# Each always-run service's kind, which is its row in the diagram.
KIND = {
    "actor-service": "posts", "text-service": "posts",
    "identity-image-service": "posts",
    "feed-service": "people", "socialgraph-service": "people", "like-service": "people",
    "notification-service": "people",
    "search-service": "finding", "hashtag-service": "finding", "location-service": "finding",
    "auth-service": "safety", "abuse-report-service": "safety",
}
STORES = [("MySQL", "everything kept", "#00758F", False), ("Redis", "sessions", "#DC2626", False),
          ("RabbitMQ", "the services' events", "#F97316", False),
          ("Garage", "files, or a store outside", "#0D9488", True)]
JOBS = ["migration-job: at each version", "account-sweeper: every 10 min",
        "file-sweeper: nightly", "mysql-backup: nightly"]


# Each recipe's own words for what the services that make profiles and
# posts give, from its k8s/instance.json: no file is everything, as on a
# site (anahita-services' docs/instance-features.md).
PROFILES = [("person", "people"), ("group", "groups"), ("event", "events"), ("website", "websites")]
POSTS = {"text-service": [("note", "notes"), ("article", "articles"), ("topic", "topics")]}
# What each service's posts are called, for a sentence.
POSTS_ARE = {"text-service": "Its posts"}


def offers(recipe):
    """What the recipe's instance.json offers, by service: a list of kinds,
    None for everything, or [] for a service it turns off."""
    import json
    path = ROOT / recipe / "k8s" / "instance.json"
    said = {}
    if path.exists():
        for each in json.loads(path.read_text()):
            said[each["service"]] = [] if each.get("enabled") is False else each.get("node_types")
    return said


def words(pairs, kinds):
    names = [name for kind, name in pairs if kinds is None or kind in kinds]
    return names


def joined(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def always_for(recipe):
    """ALWAYS, with what actor-service and text-service give
    in this recipe; and their sentences for its table."""
    said = offers(recipe)
    profiles = words(PROFILES, said.get("actor-service"))
    if "person" not in [k for k, _ in PROFILES if k in (said.get("actor-service") or [])] and said.get("actor-service") is not None:
        profiles = ["people"] + profiles
    gives, says = {}, {}
    # Every kind is too long for its box, and says no more.
    gives["actor-service"] = ("every kind of profile" if len(profiles) == len(PROFILES)
                              else ", ".join(profiles))
    says["actor-service"] = f"Every kind of profile it offers: {joined(profiles)}."
    says["search-service"] = f"Search for {joined(profiles + ['posts', 'shared feeds'])}."
    for service, pairs in POSTS.items():
        names = words(pairs, said.get(service))
        if not names and "reply" in (said.get(service) or []):
            # Replies alone: no posts of its own, the replies under the
            # others' (anahita-services' docs/instance-features.md).
            gives[service] = "replies"
            says[service] = (f"The replies under any post. {article(recipe).capitalize()} takes no notes, "
                             "articles or topics: it runs for the replies.")
        elif names:
            gives[service] = ", ".join(names)
            says[service] = (joined(names).capitalize() + ", and the replies to any post."
                             if service == "text-service" else "Photo posts.")
        else:
            gives[service] = "off here"
            says[service] = (f"{POSTS_ARE[service]}, which {article(recipe)} does not offer: "
                             "it runs, and takes none.")
    return [(name, gives.get(name, line)) for name, line in ALWAYS], says


def article(recipe):
    return "an " + recipe if recipe[0] in "aeiou" else "a " + recipe


def text(x, y, words, size=13, color=INK, anchor="middle", weight=None, spacing=None):
    w = f' font-weight="{weight}"' if weight else ""
    s = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}"{w}{s}>'
            f'{escape(words)}</text>')


def label(x, y, words):
    """A section's name: small capitals, quiet."""
    return text(x, y, words.upper(), 9.5, FAINT, anchor="start", weight="700", spacing="0.8")


def card(x, y, w, h, title, line=None, dashed=False, dot=None, dark=False, faded=False):
    """A white card with a soft shadow; a dot of colour before its title."""
    stroke = FAINT if dashed else BORDER
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    shadow = "" if dashed or faded else ' filter="url(#shadow)"'
    fill = INK if dark else (PANEL if faded else CARD)
    ink = CARD if dark else (FAINT if faded else INK)
    muted = "#CBD5E1" if dark else (FAINT if faded else MUTED)
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}"{dash}{shadow}/>']
    cx = x + w / 2
    if dot or faded:
        cy = y + h / 2 - (7 if line else 0)
        parts.append(f'<circle cx="{x + 14}" cy="{cy}" r="3.5" fill="{dot}"/>' if dot else
                     f'<circle cx="{x + 14}" cy="{cy}" r="3" fill="none" stroke="{FAINT}" stroke-width="1.2"/>')
        cx, anchor = x + 24, "start"
    else:
        anchor = "middle"
    if line:
        parts.append(text(cx, y + h / 2 - 3, title, 12, ink, anchor, "600"))
        parts.append(text(cx, y + h / 2 + 13, line, 10.5, muted, anchor))
    else:
        parts.append(text(cx, y + h / 2 + 4, title, 12, ink, anchor, "600"))
    return "\n".join(parts)


def service(x, y, w, name, gives, colour):
    """A service: a bar of its kind's colour, its name, and what it gives."""
    return "\n".join([
        f'<rect x="{x}" y="{y}" width="{w}" height="44" rx="6" fill="{CARD}" stroke="{BORDER}" filter="url(#shadow)"/>',
        f'<rect x="{x}" y="{y + 8}" width="3" height="28" rx="1.5" fill="{colour}"/>',
        text(x + w / 2 + 1, y + 19, name, 11, INK, weight="600"),
        text(x + w / 2 + 1, y + 34, gives, 10, MUTED),
    ])


def arrow(d, outside=False):
    colour, marker = (FAINT, "out") if outside else (SLATE, "in")
    dash = ' stroke-dasharray="4 3"' if outside else ""
    return (f'<path d="{d}" stroke="{colour}" stroke-width="1.6" fill="none"{dash} '
            f'marker-end="url(#{marker})"/>')


def version(recipe):
    path = ROOT / recipe / "k8s" / "kustomization.yml"
    for line in path.read_text().splitlines():
        if line.strip().startswith("newTag:"):
            return line.split(":", 1)[1].strip()
    return ""


def draw(recipe, offered):
    out = []
    always, _ = always_for(recipe)
    gives = dict(always)
    off_here = {name for name, line in always if "off here" in line}
    picks = [OPTIONAL[key] for key in offered]
    left_out = [OPTIONAL[key] for key in OPTIONAL if key not in offered]

    # Where each part goes, top to bottom.
    clients = 112
    frame = 196
    door = frame + 44
    panel = door + 84
    grid = panel + 40
    rows = [[n for n, _ in ALWAYS if KIND[n] == k] for k in ("posts", "people", "finding", "safety")]
    shared_label = grid + len(rows) * 52 + 14
    shared = shared_label + 12
    left_h = shared + 44 + 16 - panel
    off_label = grid + len(picks) * 50 + (14 if picks else 0)
    right_h = (off_label + 12 + len(left_out) * 50 if left_out else grid + len(picks) * 50) + 6 - panel
    kept_label = panel + max(left_h, right_h) + 32
    kept = kept_label + 12
    clock_label = kept + 44 + 28
    clock = clock_label + 12
    frame_bottom = clock + 36 + 20
    outside = frame_bottom + 40
    height = outside + 52 + 32

    out.append(f'<rect width="960" height="{height}" rx="16" fill="{PAGE}"/>')
    out.append(text(32, 50, f"What runs on {article(recipe)} server", 22, INK, "start", "700"))
    out.append(text(32, 72, f"The {recipe} recipe · Anahita {version(recipe)} · each box a pod", 12, MUTED, "start"))

    # What the colours mean.
    out.append(f'<rect x="560" y="20" width="376" height="72" rx="8" fill="{CARD}" stroke="{BORDER}"/>')
    for i, (colour, words) in enumerate(LEGEND):
        x, y = 576 + (i % 2) * 180, 40 + (i // 2) * 20
        if colour == "dashed":
            out.append(f'<rect x="{x - 4}" y="{y - 8}" width="16" height="10" rx="2" fill="{CARD}" stroke="{FAINT}" stroke-dasharray="3 2"/>')
            out.append(f'<circle cx="{x + 4}" cy="{y - 3}" r="2" fill="{COLOURS["offered"]}"/>')
        else:
            out.append(f'<rect x="{x - 4}" y="{y - 8}" width="3" height="10" rx="1.5" fill="{colour}"/>')
        out.append(text(x + 18, y + 1, words, 11, INK, "start"))

    # Who sends requests.
    out.append(card(160, clients, 240, 52, "Client-side apps", "browser, mobile"))
    out.append(card(560, clients, 240, 52, "Other servers", "the fediverse, the Atmosphere"))

    # The server.
    out.append(f'<rect x="20" y="{frame}" width="920" height="{frame_bottom - frame}" rx="12" fill="{PANEL}" stroke="{BORDER}"/>')
    out.append(label(36, frame + 22, "One server, running k3s"))
    for d in [f"M280 {clients + 52} L392 {door - 4}", f"M680 {clients + 52} L448 {door - 4}",
              f"M320 {door + 24} L268 {door + 24}", f"M520 {door + 24} L572 {door + 24}",
              f"M640 {door + 48} L560 {panel - 4}", f"M720 {door + 48} L770 {panel - 4}"]:
        out.append(arrow(d))
    out.append(card(48, door, 216, 48, "web-shell", "the web app, and links shared"))
    out.append(card(324, door, 192, 48, "Traefik", "HTTPS, cert-manager's certificates"))
    out.append(card(576, door, 216, 48, "gateway", "nginx: routes, checks sign-ins", dark=True))

    # Always run, a row for each kind, then the three shared ones.
    out.append(f'<rect x="36" y="{panel}" width="592" height="{left_h}" rx="10" fill="{CARD}" stroke="{BORDER}"/>')
    out.append(label(52, panel + 24, "Always run · the API"))
    for r, names in enumerate(rows):
        for c, name in enumerate(names):
            colour = FAINT if name in off_here else COLOURS[KIND[name]]
            out.append(service(52 + c * 142, grid + r * 52, 134, name, gives[name], colour))
    out.append(label(52, shared_label, "Shared by the others, over gRPC"))
    for i, (name, line) in enumerate(SHARED):
        out.append(service(52 + i * 189, shared, 181, name, line, COLOURS["shared"]))

    # Only if the site offers it; and what it does not run.
    out.append(f'<rect x="644" y="{panel}" width="280" height="{right_h}" rx="10" fill="{CARD}" stroke="{BORDER}"/>')
    out.append(label(660, panel + 24, "Only if the site offers it"))
    for i, (what, names) in enumerate(picks):
        out.append(card(660, grid + i * 50, 248, 42, what, names, dashed=True, dot=COLOURS["offered"]))
    if left_out:
        out.append(label(660, off_label, "Not run here"))
        for i, (what, names) in enumerate(left_out):
            out.append(card(660, off_label + 12 + i * 50, 248, 42, what, names, dashed=True, faded=True))

    # What keeps the data, and what runs by the clock.
    out.append(label(52, kept_label, "Kept"))
    for i, (name, line, colour, dashed) in enumerate(STORES):
        out.append(card(52 + i * 148, kept, 140, 44, name, line, dashed=dashed, dot=colour))
    out.append(label(52, clock_label, "By the clock, and once"))
    for i, words in enumerate(JOBS):
        x = 52 + i * 220
        out.append(f'<rect x="{x}" y="{clock}" width="212" height="36" rx="6" fill="{CARD}" stroke="{FAINT}" stroke-dasharray="4 3"/>')
        out.append(text(x + 106, clock + 22, words, 11.5, INK))

    # Outside the server.
    for x in (160, 480, 800):
        out.append(arrow(f"M{x} {frame_bottom} L{x} {outside - 4}", outside=True))
    out.append(card(60, outside, 200, 52, "Mail provider", "SMTP: sign-in codes, notices"))
    out.append(card(380, outside, 200, 52, "Object store", "S3: files, if not Garage", dashed=True))
    out.append(card(700, outside, 200, 52, "DNS", "the site's names"))

    # In a sentence: lower case but for names (Bluesky, GIFs), the last two
    # joined by "and" and the rest by commas, the list's own "and" kept.
    def said(what):
        return what if what.startswith("Bluesky") else what[0].lower() + what[1:]
    def listed(names):
        names = [said(n) for n in names]
        return names[0] if len(names) == 1 else "; ".join(names[:-1]) + "; and " + names[-1]
    brings = listed([what for what, _ in picks])
    gone = (" Not run: " + listed([what for what, _ in left_out]) + ".") if left_out else ""
    desc = (f"One server running k3s. Traefik, with certificates from cert-manager, takes every request, from "
            f"client-side apps and from other servers, and hands it to the gateway, or to web-shell for the web app. "
            f"The gateway routes the API to {len(ALWAYS)} services that always run, each with what it gives: "
            + "; ".join(f"{n}, {g}" for n, g in always)
            + f". Three are shared over gRPC: the graph, files and email. {len(picks)} others, drawn dashed, run "
            f"because {article(recipe)} offers what they bring: {brings}.{gone} MySQL, Redis, RabbitMQ and Garage keep the "
            f"data; four jobs run by the clock or once. Outside the server: a mail provider, an object store if not "
            f"Garage, and DNS.")
    marker = ('<marker id="{0}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" '
              'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{1}"/></marker>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" width="960" height="{height}" '
            f'font-family="Inter, \'SF Pro Text\', \'Segoe UI\', Helvetica, Arial, sans-serif" role="img" '
            f'aria-labelledby="title desc">\n'
            f'<title id="title">What runs on {article(recipe)} server</title>\n<desc id="desc">{escape(desc)}</desc>\n'
            f'<defs>\n<filter id="shadow" x="-10%" y="-10%" width="120%" height="140%"><feDropShadow dx="0" dy="1.5" '
            f'stdDeviation="2.5" flood-color="{INK}" flood-opacity="0.08"/></filter>\n'
            + marker.format("in", SLATE) + "\n" + marker.format("out", FAINT) + "\n</defs>\n"
            + "\n".join(out) + "\n</svg>\n")


# What each service does, a sentence each, for the table under the
# diagram in each recipe's README.
SAYS = {
    "auth-service": "Signing in and signing up, and the accounts people sign in with.",
    "actor-service": "Every kind of profile: people, groups and events, and the profiles of websites.",
    "text-service": "Notes, articles and topics, and the replies to any post.",
    "feed-service": "The chronological feed, reposts, and the custom feeds people make.",
    "socialgraph-service": "Who follows, blocks, mutes and subscribes to whom.",
    "like-service": "Likes.",
    "notification-service": "Notifications in the app.",
    "search-service": "Search for people, groups, events, posts and shared feeds.",
    "hashtag-service": "Hashtags.",
    "location-service": "The locations posts are tagged with, and finding them on a map.",
    "identity-image-service": "Profile and cover photos, made afresh at each size.",
    "abuse-report-service": "Reports of people and posts, and the cases administrators decide.",
    "graph-grpc-service": "The graph every other service reads: profiles and posts are its nodes, and the ties between them its edges.",
    "file-grpc-service": "Files, in Garage or any S3-compatible store.",
    "mail-grpc-service": "Email, over SMTP.",
    "web-shell": "Serves the web app, each page with its own title and picture, so that a shared link shows as itself.",
    "photos": "Photo posts, and the pictures in a reply.",
    "video": "Video, GIF and audio posts; video-worker makes each ready for every screen.",
    "fediverse": "Makes the site a server of the fediverse, for the people who choose to be found there.",
    "atmosphere": "Bluesky and the rest of the Atmosphere: following profiles there, and posting there for whoever connects their own account.",
    "websites": "Following a website's feed like a profile; syndication-worker reads every feed and posts what is new.",
    "cards": "The card under a note that links to a page: its title and picture.",
    "follow": "Recommendations of who to follow.",
    "data": "A copy of one's own data to download, and a social graph brought in from elsewhere; import-export-worker does each.",
}
START, END = "<!-- what-runs:start -->", "<!-- what-runs:end -->"


def table(recipe, offered):
    rows = [("web-shell", SAYS["web-shell"])]
    _, own = always_for(recipe)
    rows += [(name, own.get(name, SAYS[name])) for name, _ in ALWAYS + SHARED]
    rows += [(OPTIONAL[key][1], SAYS[key]) for key in offered]
    lines = ["| Service | What it does |", "| --- | --- |"]
    lines += [f"| {', '.join(f'`{n.strip()}`' for n in names.split(','))} | {says} |" for names, says in rows]
    return (START + "\n\n**What each service does,** of those it runs:\n\n" + "\n".join(lines) + "\n\n" + END)


def readme(recipe, offered):
    path = ROOT / recipe / "README.md"
    words = path.read_text()
    if START in words:
        before, rest = words.split(START, 1)
        after = rest.split(END, 1)[1]
        words = before + table(recipe, offered) + after
    else:
        # The first time: after the paragraph that follows the diagram.
        at = words.index("](images/what-runs.svg)")
        at = words.index("\n\n", words.index("\n\n", at) + 2) + 2
        words = words[:at] + table(recipe, offered) + "\n\n" + words[at:]
    path.write_text(words)


if __name__ == "__main__":
    for recipe, offered in RECIPES.items():
        path = ROOT / recipe / "images" / "what-runs.svg"
        path.write_text(draw(recipe, offered))
        readme(recipe, offered)
        print(path.relative_to(ROOT), "and its README")
