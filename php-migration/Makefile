# php-migration's tasks: moving a site from Anahita PHP into a commons site,
# and thinning it. `make` alone lists them.
#
# Each task that changes anything first counts what it would change, and
# changes nothing; the same task with -apply does it. Each that removes
# keeps a copy of what it removes first, in kept/.
#
# SITE is the commons folder of the new site, ../commons unless said. Its
# tunnel must be open: make tunnel, there.

SITE ?= ../commons
MIGRATE = python3 -I migration/migrate.py --site $(SITE) \
  $(if $(AS),--as $(AS)) $(if $(DUMP),--dump $(DUMP)) $(if $(FILES),--files $(FILES)) \
  $(if $(BEFORE),--before $(BEFORE)) $(if $(KEEP),--keep $(KEEP)) $(if $(WHO),--who $(WHO)) \
  $(if $(FROM),--from $(FROM)) $(if $(TO),--to $(TO)) $(if $(ALL),--all) \
  $(if $(GROUPS),--groups $(GROUPS)) $(if $(EMPTY),--empty)

.DEFAULT_GOAL := help
TASKS := archive files database check files-tidy inactive old-posts no-author move-photos groups sweep
.PHONY: help $(TASKS) $(addsuffix -apply,$(TASKS))

## help: this list
help:
	@sed -n 's/^## //p' $(MAKEFILE_LIST) | awk -F': ' '{ printf "  %-13s %s\n", $$1, substr($$0, length($$1) + 3) }'

## archive: DUMP= FILES=: describes the old site's dump and files, and proves the dump opens
archive:
	$(MIGRATE) archive

## files: FILES=: what would go into the new site's files; files-apply copies them, in today's layout
files:
	$(MIGRATE) files
files-apply:
	$(MIGRATE) files --apply

## database: DUMP=: what would be replaced; database-apply loads the old database and upgrades it
database:
	$(MIGRATE) database
database-apply:
	$(MIGRATE) database --apply

## check: what there is, and whether it is whole
check:
	$(MIGRATE) check

## files-tidy: what is left of the old layout; files-tidy-apply removes each file whose copy is in place
files-tidy:
	$(MIGRATE) files-tidy
files-tidy-apply:
	$(MIGRATE) files-tidy --apply

## inactive: BEFORE= [KEEP=a,b]: people not seen since then who wrote nothing; -apply removes them
inactive:
	$(MIGRATE) inactive
inactive-apply:
	$(MIGRATE) inactive --apply

## old-posts: BEFORE= [WHO=]: notes, articles and topics older than that; -apply removes them
old-posts:
	$(MIGRATE) old-posts
old-posts-apply:
	$(MIGRATE) old-posts --apply

## no-author: posts whose author is gone; -apply removes them
no-author:
	$(MIGRATE) no-author
no-author-apply:
	$(MIGRATE) no-author --apply

## move-photos: FROM= TO= [ALL=1]: photos to move to a profile; -apply moves them with their files
move-photos:
	$(MIGRATE) move-photos
move-photos-apply:
	$(MIGRATE) move-photos --apply

## groups: GROUPS=a,b or EMPTY=1: groups to remove with what is in them; -apply removes them
groups:
	$(MIGRATE) groups
groups-apply:
	$(MIGRATE) groups --apply

## sweep: sweep-apply runs the nightly sweep at once: hashtags and locations no post carries
sweep:
	$(MIGRATE) sweep
sweep-apply:
	$(MIGRATE) sweep --apply
