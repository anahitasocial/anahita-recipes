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
    ("photo-service", "photos"),
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
    "coffeehouse": SOCIAL,
    "journal": SOCIAL,
    "theatre": ["video"] + SOCIAL,
    "gathering": SOCIAL,
}

INK, MUTED, LINE, CARD, BORDER, GREY = "#202124", "#5f6368", "#5f6368", "#fff", "#dadce0", "#f1f3f4"


def text(x, y, words, size=13, color=INK, anchor="middle", weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}"{w}>{escape(words)}</text>'


def box(x, y, w, h, title, line=None, dashed=False, rx=10, size=14):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{CARD}" stroke="{INK}" stroke-width="1.5"{dash}/>']
    if line:
        parts.append(text(x + w / 2, y + h / 2 - 3, title, size))
        parts.append(text(x + w / 2, y + h / 2 + 14, line, 11, MUTED))
    else:
        parts.append(text(x + w / 2, y + h / 2 + 5, title, size))
    return "\n".join(parts)


def service(x, y, w, name, gives):
    """A service always run: its name, and what it gives under it."""
    return "\n".join([
        f'<rect x="{x}" y="{y}" width="{w}" height="42" rx="6" fill="{GREY}" stroke="#bdc1c6"/>',
        text(x + w / 2, y + 18, name, 11),
        text(x + w / 2, y + 33, gives, 10, MUTED),
    ])


def arrow(d):
    return f'<path d="{d}" stroke="{LINE}" stroke-width="1.5" fill="none" marker-end="url(#arrow)"/>'


def draw(recipe, offered):
    out = []
    # The front door.
    door = 150
    # Always run: 13 services in four columns, then the shared ones.
    panel = 236
    grid = panel + 36
    rows = (len(ALWAYS) + 3) // 4
    shared_label = grid + rows * 50 + 22
    shared = shared_label + 10
    panel_h = shared + 42 + 16 - panel
    # Only if the site offers it.
    picks = [OPTIONAL[key] for key in offered]
    right_h = 36 + len(picks) * 46 + 10
    # Kept, and by the clock, under the panels.
    kept_label = max(panel + panel_h, panel + right_h) + 30
    kept = kept_label + 10
    clock_label = kept + 44 + 32
    clock = clock_label + 10
    frame_bottom = clock + 36 + 16
    outside = frame_bottom + 32
    height = outside + 52 + 28

    out.append(f'<rect width="960" height="{height}" rx="16" fill="#fafafa"/>')
    # Who sends requests.
    out.append(box(160, 24, 240, 52, "Client-side apps", "browser, mobile"))
    out.append(box(640, 24, 240, 52, "Other servers", "the fediverse, the Atmosphere"))
    # The server.
    out.append(f'<rect x="20" y="104" width="920" height="{frame_bottom - 104}" rx="14" fill="none" stroke="{INK}" stroke-width="1.5"/>')
    out.append(text(40, 128, "One server, running k3s", 13, anchor="start", weight="600"))
    for d in ["M220 76 L385 146", "M740 76 L425 146", "M300 174 L264 174", "M510 174 L546 174",
              f"M598 198 L520 {panel - 4}", f"M698 198 L758 {panel - 4}"]:
        out.append(arrow(d))
    out.append(box(44, door, 216, 48, "web-shell", "the web app, and links shared", dashed=True))
    out.append(box(300, door, 210, 48, "Traefik", "HTTPS, cert-manager's certificates"))
    out.append(box(550, door, 200, 48, "gateway", "nginx: routes, checks sign-ins"))

    out.append(f'<rect x="36" y="{panel}" width="580" height="{panel_h}" rx="10" fill="{CARD}" stroke="{BORDER}" stroke-width="1.5"/>')
    out.append(text(52, panel + 22, "Always run", 13, anchor="start", weight="600"))
    out.append(text(140, panel + 22, "the API, and what each gives", 11, MUTED, anchor="start"))
    for i, (name, gives) in enumerate(ALWAYS):
        out.append(service(52 + (i % 4) * 140, grid + (i // 4) * 50, 132, name, gives))
    out.append(text(52, shared_label, "Shared by the others, over gRPC", 11, MUTED, anchor="start"))
    for i, (name, gives) in enumerate(SHARED):
        out.append(service(52 + i * 187, shared, 178, name, gives))

    out.append(f'<rect x="632" y="{panel}" width="292" height="{right_h}" rx="10" fill="{CARD}" stroke="{BORDER}" stroke-width="1.5"/>')
    out.append(text(648, panel + 22, "Only if the site offers it", 13, anchor="start", weight="600"))
    for i, (what, names) in enumerate(picks):
        y = grid + i * 46
        out.append(f'<rect x="648" y="{y}" width="260" height="40" rx="8" fill="{CARD}" stroke="{INK}" stroke-width="1.2" stroke-dasharray="5 4"/>')
        out.append(text(662, y + 17, what, 13, anchor="start"))
        out.append(text(662, y + 32, names, 10.5, MUTED, anchor="start"))

    out.append(text(52, kept_label, "Kept", 13, anchor="start", weight="600"))
    for i, (name, line, dashed) in enumerate([("MySQL", "everything kept", False), ("Redis", "sessions", False),
                                              ("RabbitMQ", "the services' events", False),
                                              ("Garage", "files, or a store outside", True)]):
        out.append(box(52 + i * 140, kept, 132, 44, name, line, dashed=dashed, rx=8, size=13))

    out.append(text(52, clock_label, "By the clock, and once", 13, anchor="start", weight="600"))
    for i, words in enumerate(["migration-job: at each version", "account-sweeper: every 10 min",
                               "file-sweeper: nightly", "mysql-backup: nightly"]):
        x = 52 + i * 220
        out.append(f'<rect x="{x}" y="{clock}" width="210" height="36" rx="6" fill="{GREY}" stroke="#bdc1c6"/>')
        out.append(text(x + 105, clock + 22, words, 12))

    for x in (160, 480, 800):
        out.append(arrow(f"M{x} {frame_bottom} L{x} {outside - 4}"))
    out.append(box(60, outside, 200, 52, "Mail provider", "SMTP: sign-in codes, notices"))
    out.append(box(380, outside, 200, 52, "Object store", "S3: files, if not Garage", dashed=True))
    out.append(box(700, outside, 200, 52, "DNS", "the site's names"))

    brings = ", ".join(what if what.startswith("Bluesky") else what.lower() for what, _ in picks)
    left_out = [OPTIONAL[k][0] for k in OPTIONAL if k not in offered]
    gone = (" " + " and ".join(w if w.startswith("Bluesky") else w.lower() for w in left_out)
            + " are not run.") if left_out else ""
    desc = (f"One server running k3s. Traefik, with certificates from cert-manager, takes every request, from "
            f"client-side apps and from other servers, and hands it to the gateway, or to web-shell for the web app. "
            f"The gateway routes the API to {len(ALWAYS)} services that always run, each with what it gives: "
            + "; ".join(f"{n}, {g}" for n, g in ALWAYS)
            + f". Three are shared over gRPC: the graph, files and email. {len(picks)} others, drawn dashed, run "
            f"because {recipe} offers what they bring: {brings}.{gone} MySQL, Redis, RabbitMQ and Garage keep the "
            f"data; four jobs run by the clock or once. Outside the server: a mail provider, an object store if not "
            f"Garage, and DNS.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" width="960" height="{height}" '
            f'font-family="system-ui, -apple-system, \'Segoe UI\', sans-serif" role="img" aria-labelledby="title desc">\n'
            f'<title id="title">What runs on a {recipe} server</title>\n<desc id="desc">{escape(desc)}</desc>\n'
            f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{LINE}"/></marker></defs>\n'
            + "\n".join(out) + "\n</svg>\n")


# What each service does, a sentence each, for the table under the
# diagram in each recipe's README.
SAYS = {
    "auth-service": "Signing in and signing up, and the accounts people sign in with.",
    "actor-service": "Every kind of profile: people, groups and events, and the profiles of websites.",
    "text-service": "Notes, articles and topics, and the replies to any post.",
    "photo-service": "Photo posts.",
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
    "video": "Video, GIF and audio posts; video-worker makes each ready for every screen.",
    "fediverse": "Makes the site a server of the fediverse, for the people who choose to be found there.",
    "atmosphere": "Bluesky and the rest of the Atmosphere: following profiles there, and posting there for whoever connects their own account.",
    "websites": "Following a website's feed like a profile; syndication-worker reads every feed and posts what is new.",
    "cards": "The card under a note that links to a page: its title and picture.",
    "follow": "Recommendations of who to follow.",
    "data": "A copy of one's own data to download, and a social graph brought in from elsewhere; import-export-worker does each.",
}
START, END = "<!-- what-runs:start -->", "<!-- what-runs:end -->"


def table(offered):
    rows = [("web-shell", SAYS["web-shell"])]
    rows += [(name, SAYS[name]) for name, _ in ALWAYS + SHARED]
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
        words = before + table(offered) + after
    else:
        # The first time: after the paragraph that follows the diagram.
        at = words.index("](images/what-runs.svg)")
        at = words.index("\n\n", words.index("\n\n", at) + 2) + 2
        words = words[:at] + table(offered) + "\n\n" + words[at:]
    path.write_text(words)


if __name__ == "__main__":
    for recipe, offered in RECIPES.items():
        path = ROOT / recipe / "images" / "what-runs.svg"
        path.write_text(draw(recipe, offered))
        readme(recipe, offered)
        print(path.relative_to(ROOT), "and its README")
