# Where to run a recipe

A recipe runs on one server with k3s. Any provider that rents a virtual
server will do; this page says which have been tried, which are next, and
which should work but nobody has tried yet.

## What the server needs

| | |
| --- | --- |
| System | Ubuntu 24.04 LTS, ARM or x86 |
| Size | 2 virtual CPUs, 4 GB of memory, 40 GB of disk; what banu.io runs on |
| Network | a public IPv4 address; ports 22, 80 and 443 open, and nothing else |
| Access | SSH with a key; Kubernetes is reached through `make tunnel`, never opened to the internet |

Files are kept in Garage on the same server, so no other account is needed.
A provider's S3-compatible store can take its place, Cloudflare's R2 among
them; Cloudflare rents no servers to run a recipe on.

## Tried, and next

| Provider | Company from | Servers in | State |
| --- | --- | --- | --- |
| Amazon Web Services | United States | Montréal (`ca-central-1`) | Tried: banu.io has run on it since October 2026 |
| OVHcloud | France | Beauharnois, Quebec; also Europe | Not tried yet |
| Hetzner | Germany | Falkenstein, Nuremberg, Helsinki | Not tried yet |

Hetzner, OVHcloud, netcup and DigitalOcean are among the hosts fediverse
servers run on most, in [FediDB's statistics](https://fedidb.com/stats).
OVHcloud and Hetzner both rent a server to anybody with a card, with an API
to make one. **We have not run
Anahita on either yet.** If you do, tell us how it went, what worked and
what did not, in an issue on
[anahita-recipes](https://github.com/anahitasocial/anahita-recipes/issues).

## Candidates nobody has tried

These should work in theory: each rents virtual servers with Ubuntu, in the
places named. We have not tried them, and what is said here is from the
providers' own pages. A report on any of them, in an issue, is welcome.

### In Canada

| Provider | Company from | Servers in | Notes |
| --- | --- | --- | --- |
| ThinkOn | Canada | Ottawa, Toronto and other Canadian cities | Built for organisations rather than one person: begins with a trial and a talk with sales. Gander Social runs on it, and on OVHcloud |
| Cloudspace | Canada | Edmonton | Says it has an API and a command line to make servers |
| Canadian Web Hosting | Canada | Vancouver, Toronto | |
| FullHost | Canada | Victoria | |
| DigitalOcean | United States | Toronto | |
| Vultr | United States | Toronto | |
| Akamai (Linode) | United States | Toronto | |

### In Europe

| Provider | Company from | Servers in | Notes |
| --- | --- | --- | --- |
| Scaleway | France | Paris, Amsterdam, Warsaw | |
| IONOS | Germany | Germany, Spain, the United Kingdom, among others | |
| netcup | Germany | Nuremberg, Vienna, Amsterdam | |
| UpCloud | Finland | Helsinki, Frankfurt, Amsterdam, Madrid, Warsaw, among others | |
| Exoscale | Switzerland | Geneva, Zurich, Frankfurt, Munich, Vienna, Sofia, Zagreb | |
| Infomaniak | Switzerland | Geneva, Winterthur | |

A provider whose servers are in the country, and a company from the
country, are two different things; the tables show both, for those to whom
it matters.
