# php-migration

Moving a site from Anahita PHP to today's Anahita, the way banu.io was
moved in October 2026, then thinning what years have left in it.

It holds the move alone. The new site is a [`commons`](../commons) site:
make it first, following its README as far as `make apply`, and this
recipe moves the old site into it.

**Not tried yet as a recipe.** but we used similar scripts to migrate the old anahita.io to banu.io 

If anything goes wrong open an [issue](https://github.com/anahitasocial/anahita-recipes/issues).

## Contents

1. [How it keeps you safe](#how-it-keeps-you-safe)
2. [What you need](#what-you-need)
3. [The move](#the-move)
4. [Thinning the site](#thinning-the-site)
5. [Retiring the old site](#retiring-the-old-site)

## How it keeps you safe

1. **The old site is only read.** Its dump and its files are copied from;
   nothing here changes them. Until the old site is retired, it is the copy
   to go back to.
2. **Every task first counts.** `make database` says what would be
   replaced, `make inactive` who would be removed, and nothing changes. The
   same task with `-apply` does it.
3. **What is removed is kept first,** in full, in `kept/`, readable by you
   alone. Look at the result before you delete those copies.
4. **The move can be done again.** `make database-apply` replaces the
   whole of the new site's database with the old one each time, so a move
   that went wrong, or thinning you regret, is undone by doing it again
   from the dump.

## What you need

1. **A `commons` site,** made as its README says, as far as `make apply`,
   with its tunnel open (`make tunnel`, in its folder).
2. **The old site's database,** as a dump: `mysqldump --single-transaction
   <database> | gzip > old-site.sql.gz` on the old server.
3. **The old site's files:** the folder that holds its `assets/`, copied
   here, from the old server (`rsync`) or from its bucket (`aws s3 sync
   s3://<bucket>/assets ./old-files/assets`).
4. **On your computer,** besides what `commons` needs: Python 3, and Go,
   which runs anahita-services' tool for the files.

If the new site's folder is not `../commons`, name it on each task:
`SITE=<folder>`.

## The move

1. **`make archive DUMP=old-site.sql.gz FILES=old-files`.** Describes the
   dump (its size and checksum) and the files (how many, how large), and
   proves the dump opens: it loads it into a database of its own on the new
   site's MySQL, counts the people and the posts, and drops it. Keep the
   dump and the files where they cannot be changed.
2. **`make database DUMP=old-site.sql.gz`,** then
   **`make database-apply DUMP=old-site.sql.gz`.** Replaces the new site's
   database with the old one, after you type the domain, then runs the
   migration job, which finds the PHP tables and upgrades them, and starts
   every service again. The first super administrator `make init` made is
   replaced too: from here on, you sign in as the old site's administrators,
   with their passwords.
3. **`make files FILES=old-files`,** then **`make files-apply
   FILES=old-files`.** Uploads the old files to the new site's, then moves
   them to where today's Anahita looks for them (anahita-services'
   `scripts/s3-migration -from v0`, at the version the site runs).
4. **`make check`.** What there is, by kind, and whether it is whole: no
   post without its owner or its parent, no link without both ends, and as
   many photo files stored as are named. Then look at the site.
5. **`make files-tidy`,** then **`make files-tidy-apply`,** once the site
   shows its pictures: the files in the old layout, each removed only when
   its copy is in place.

## Thinning the site

A site that has run for years carries what nobody needs any more. These are
the examples done for banu.io, made general; each counts first, keeps a copy
of what it removes, and removes through the API, as the web app would, so
that counts, hashtags and threads stay right. They sign in as an
administrator: the only super administrator, or the one named with
`AS=<handle>`, and ask for the password.

| Task | What it removes |
| --- | --- |
| `make inactive BEFORE=2020-01-01 KEEP=picard,sisko` | People who have not visited since that day and wrote nothing, with what they own. Administrators stay, and those named in `KEEP` |
| `make old-posts BEFORE=2017-01-01` | Notes, articles and topics written before that day, with their threads; `WHO=<handle>` for one person's alone. Photos stay |
| `make no-author` | Posts whose author is gone, shown to nobody |
| `make move-photos FROM=<group> TO=<person>` | Nothing: it moves the photos `TO` posted in a group or on a profile to their own profile, with their files. `ALL=1` moves every photo there |
| `make groups GROUPS=<group>,<group>` | Groups, with everything in them; `EMPTY=1` for every group with no posts. Move out first what is to be kept |
| `make sweep-apply` | Hashtags and locations no post carries any more, at once rather than at night |

Each with `-apply` does it: `make inactive-apply BEFORE=2020-01-01`.
Stored files that nothing names any more are removed every night by the
site itself (`FILE_SWEEP=on`).

## Retiring the old site

Once the new site has been looked at, and people have been told:

1. Make the old site read-only, or take it down, and point its domain at
   the new site, if they share one.
2. Keep the dump and the files, somewhere they cannot be deleted by
   mistake, for as long as you may need to go back.
3. Then remove the old server and its database, at its provider.

These are your provider's steps, not this recipe's.
