#!/usr/bin/env python3
# Moves a site from Anahita PHP into a commons site, and thins it: the
# tasks of php-migration's Makefile, which names each one. Made general from
# what was done for banu.io in October 2026.
#
#   python3 -I migration/migrate.py <task> --site <commons folder> [--apply] [options]
#
# Every task that changes anything first counts what it would change, and
# changes nothing; with --apply it does it. Every task that removes keeps a
# copy of what it removes first, in kept/, readable by you alone.
#
# The site is reached as make reaches it: its own kubeconfig and context,
# through the tunnel (make tunnel, in the site's folder), its MySQL by
# kubectl exec, its files at https://files.<domain>, and its API signed in as
# an administrator of yours, as the web app signs in.
import argparse, base64, datetime, getpass, gzip, hashlib, html, http.cookiejar, json, os, re
import secrets, shutil, ssl, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KEPT = os.path.join(os.path.dirname(HERE), 'kept')

PERSON = 'node.actor.person-service.person.v1'
GROUP = 'node.actor.group-service.group.v1'
PHOTO = 'node.medium.photo-service.photo.v1'
KINDS = {
    'node.medium.text-service.note.v1': 'notes',
    'node.medium.text-service.article.v1': 'articles',
    'node.medium.text-service.topic.v1': 'topics',
}
PHOTOS = 'assets/v1/photo-service/photo'
CLIENT = 'anahita-web'
SCOPES = 'openid profile email offline_access media:read media:write'


# --- The site: its folder, its cluster, its MySQL and its files.

def env_file(path):
    values = {}
    if os.path.exists(path):
        for line in open(path):
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.rstrip('\n').split('=', 1)
                values[key.strip()] = value
    return values


class Site:
    def __init__(self, args):
        self.args = args
        folder = os.path.abspath(args.site)
        self.folder = folder
        self.site = env_file(os.path.join(folder, 'site.env'))
        self.config = env_file(os.path.join(folder, 'k8s', 'config.env'))
        self.secrets = env_file(os.path.join(folder, 'k8s', 'secrets.env'))
        self.domain = self.site.get('DOMAIN')
        if not self.domain:
            sys.exit(f'No site in {folder}: name the commons folder with SITE=, after its make init.')
        self.kubeconfig = os.path.expanduser(f'~/.kube/{self.domain}.yaml')
        self.kubectl_base = ['kubectl', '--kubeconfig', self.kubeconfig, '--context', self.domain, '-n', 'anahita']
        self.bucket = self.config.get('STORAGE_BUCKET', 'anahita')
        self.api = f'https://api.{self.domain}'
        self.auth = f'https://auth.{self.domain}'
        self.redirect = f'https://{self.domain}/oauth/callback'
        self.headers = None

    def kubectl(self, *a, stdin=None, check=True):
        out = subprocess.run(self.kubectl_base + list(a), input=stdin, capture_output=True)
        if check and out.returncode:
            sys.exit(f'kubectl {" ".join(a[:3])}: ' + out.stderr.decode()[-400:]
                     + '\nIs the tunnel open? make tunnel, in the site\'s folder.')
        return out.stdout.decode()

    def mysql(self, statements, database='anahita'):
        """SQL in the site's MySQL, from standard input, so that nothing in it
        is read by a shell; the root password stays in the pod. In utf8mb4,
        as the rows are kept, and raw, so that JSON keeps its own escapes."""
        data = statements if isinstance(statements, bytes) else statements.encode()
        out = subprocess.run(self.kubectl_base + ['exec', '-i', 'mysql-0', '--', 'sh', '-c',
                             f'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 --raw -N {database}'],
                             input=data, capture_output=True)
        if out.returncode:
            sys.exit('mysql: ' + out.stderr.decode().replace(
                'mysql: [Warning] Using a password on the command line interface can be insecure.\n', '')[-600:])
        return [line.split('\t') for line in out.stdout.decode().strip().split('\n') if line]

    def load(self, path, database):
        """A dump into a database, streamed, without its own CREATE DATABASE
        and USE, so that it goes into the database it is given."""
        run = subprocess.Popen(self.kubectl_base + ['exec', '-i', 'mysql-0', '--', 'sh', '-c',
                               f'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4 {database}'],
                               stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        opened = gzip.open(path) if path.endswith('.gz') else open(path, 'rb')
        with opened as f:
            for line in f:
                if not re.match(rb'^(CREATE DATABASE|USE) ', line):
                    run.stdin.write(line)
        run.stdin.close()
        error = run.stderr.read().decode()
        if run.wait():
            sys.exit('mysql: ' + error.replace(
                'mysql: [Warning] Using a password on the command line interface can be insecure.\n', '')[-600:])

    def s3_env(self):
        """The site's Garage, as an S3 store, for the AWS CLI: its address, the
        site's own key, paths with the bucket in them. Nothing of yours in
        ~/.aws is read."""
        config = tempfile.NamedTemporaryFile('w', delete=False, suffix='.aws')
        config.write('[default]\ns3 =\n  addressing_style = path\n')
        config.close()
        env = dict(os.environ, AWS_CONFIG_FILE=config.name, AWS_SHARED_CREDENTIALS_FILE=os.devnull,
                   AWS_DEFAULT_REGION=self.config.get('STORAGE_REGION', 'garage'),
                   AWS_ACCESS_KEY_ID=self.secrets.get('STORAGE_ACCESS_KEY', ''),
                   AWS_SECRET_ACCESS_KEY=self.secrets.get('STORAGE_SECRET_KEY', ''),
                   AWS_REQUEST_CHECKSUM_CALCULATION='when_required',
                   AWS_RESPONSE_CHECKSUM_VALIDATION='when_required')
        if not env['AWS_ACCESS_KEY_ID']:
            sys.exit(f'No STORAGE_ACCESS_KEY in {self.folder}/k8s/secrets.env.')
        return env

    def s3(self, *a, capture=False, check=True):
        need('aws', 'the AWS CLI, which speaks to Garage')
        out = subprocess.run(['aws', '--endpoint-url', f'https://files.{self.domain}', 's3'] + list(a),
                             env=self.s3_env(), capture_output=capture)
        if out.returncode and check:
            sys.exit('aws s3 ' + ' '.join(a[:2]) + (': ' + out.stderr.decode()[-400:] if capture else ' failed.'))
        return out.stdout.decode() if capture else ''

    # --- The API, signed in as an administrator, as the web app signs in.

    def opener(self):
        if not hasattr(self, '_opener'):
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *a, **k): return None
            # python.org's Python for macOS comes with no certificates of its own.
            tls = ssl.create_default_context()
            if not tls.get_ca_certs() and os.path.exists('/etc/ssl/cert.pem'):
                tls = ssl.create_default_context(cafile='/etc/ssl/cert.pem')
            self._opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), NoRedirect,
                urllib.request.HTTPSHandler(context=tls))
        return self._opener

    def request(self, method, url, body=None, headers=None):
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            resp = self.opener().open(req, timeout=120)
            return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def signin(self):
        """Signed in as the administrator named by --as, asked for their
        password (kept nowhere) and, with two-factor on, their passcode; then
        proved again, as removing people asks."""
        alias = self.args.as_
        if not alias:
            admins = self.mysql(f'SELECT alias FROM nodes WHERE type = "{PERSON}" AND person_type = "super-administrator" '
                                'AND purged_at IS NULL ORDER BY id;')
            if len(admins) != 1:
                sys.exit('Name the administrator to sign in as: AS=<handle>.')
            alias = admins[0][0]
        who = self.person(alias)
        if not hasattr(self, 'password'):
            self.password = getpass.getpass(f"@{alias}'s password: ")
            self.email = self.mysql(f'SELECT email FROM auth_accounts WHERE node_id = {who};')[0][0]
        form = lambda d: urllib.parse.urlencode(d).encode()
        F = {'Content-Type': 'application/x-www-form-urlencoded'}
        csrf = lambda b: html.unescape(re.search(r'name="csrf_token" value="([^"]+)"', b.decode()).group(1))
        said = lambda b: (lambda m: html.unescape(m.group(1)).strip() if m else '')(
            re.search(r'class="error-message"[^>]*>([^<]+)<', b.decode(errors='replace')))
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        authorize = f'{self.auth}/oauth/authorize?' + urllib.parse.urlencode({
            'response_type': 'code', 'client_id': CLIENT, 'redirect_uri': self.redirect, 'scope': SCOPES,
            'state': 'migrate', 'code_challenge': challenge, 'code_challenge_method': 'S256'})
        self.request('GET', authorize)
        st, h, b = self.request('GET', f'{self.auth}/oauth/login')
        st, h, b = self.request('POST', f'{self.auth}/oauth/login',
                                form({'identifier': self.email, 'password': self.password, 'csrf_token': csrf(b)}), F)
        if st == 200:
            sys.exit('Signing in was refused: ' + (said(b) or 'no reason given'))
        location = h.get('Location', '')
        if '/login/totp' in location:
            st, h, b = self.request('GET', urllib.parse.urljoin(self.auth, location))
            passcode = input('The passcode from your authenticator app: ').strip()
            st, h, b = self.request('POST', f'{self.auth}/oauth/login/totp',
                                    form({'totp_passcode': passcode, 'csrf_token': csrf(b)}), F)
            if st == 200:
                sys.exit('The passcode was refused: ' + (said(b) or 'no reason given'))
            location = h.get('Location', '')
        for _ in range(6):
            if 'code=' in location:
                break
            st, h, b = self.request('GET', urllib.parse.urljoin(self.auth, location) if location else authorize)
            location = h.get('Location', '')
        if 'code=' not in location:
            text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', b.decode(errors='replace')))
            sys.exit(f'Signing in stopped ({st}): {text[:200]}')
        code = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)['code'][0]
        st, h, b = self.request('POST', f'{self.auth}/oauth/token', form({
            'grant_type': 'authorization_code', 'client_id': CLIENT, 'code': code,
            'redirect_uri': self.redirect, 'code_verifier': verifier}), F)
        if st >= 300:
            sys.exit(f'The token was refused ({st}): {b[:200].decode()}')
        self.headers = {'Authorization': 'Bearer ' + json.loads(b)['access_token'], 'Content-Type': 'application/json'}
        st, h, b = self.request('POST', f'{self.api}/reauth/password', json.dumps({'password': self.password}).encode(), self.headers)
        if st >= 300:
            sys.exit(f'Proving it again was refused ({st}): {b[:200].decode()}')
        print(f'Signed in as @{alias}.')

    def call(self, method, path, body=None):
        """The API, signed in again when the token has run out."""
        data = json.dumps(body).encode() if body is not None else None
        st, h, b = self.request(method, f'{self.api}/{path}', data, self.headers)
        if st == 401:
            self.signin()
            st, h, b = self.request(method, f'{self.api}/{path}', data, self.headers)
        return st, b

    # --- What is here.

    def person(self, alias):
        alias = alias.lstrip('@')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', alias):
            sys.exit(f'Not a handle: {alias}')
        found = self.mysql(f'SELECT id FROM nodes WHERE alias = "{alias}" AND type = "{PERSON}" AND purged_at IS NULL;')
        if not found:
            sys.exit(f'Nobody is @{alias} here.')
        return int(found[0][0])

    def actor(self, alias):
        """A person or a group, by handle: its id and its type."""
        alias = alias.lstrip('@')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', alias):
            sys.exit(f'Not a handle: {alias}')
        found = self.mysql(f'SELECT id, type FROM nodes WHERE alias = "{alias}" AND type IN ("{PERSON}", "{GROUP}") '
                           'AND purged_at IS NULL;')
        if not found:
            sys.exit(f'No person or group is @{alias} here.')
        return int(found[0][0]), found[0][1]

    def keep(self, name, ids):
        """A copy of these nodes, in full, before anything goes."""
        os.makedirs(KEPT, mode=0o700, exist_ok=True)
        path = os.path.join(KEPT, f'{name}-{datetime.datetime.now():%Y%m%d-%H%M%S}.json')
        rows = []
        for start in range(0, len(ids), 2000):
            chunk = ', '.join(str(i) for i in ids[start:start + 2000])
            rows += self.mysql(f'''
SELECT JSON_OBJECT('id', id, 'type', type, 'alias', alias, 'created_at', created_at,
                   'created_by', created_by, 'parent_id', parent_id, 'root_id', root_id,
                   'owner_id', owner_id, 'name', name, 'body', body, 'last_visited_at', last_visited_at)
FROM nodes
WHERE id IN ({chunk});
''')
        with open(path, 'w') as f:
            json.dump([json.loads(r[0]) for r in rows], f, ensure_ascii=False, indent=1)
        os.chmod(path, 0o600)
        print(f'A copy of all {len(rows)} is in {path}.')
        return path


def need(tool, what):
    if not shutil.which(tool):
        sys.exit(f'{tool} is needed: {what}.')


def ids_of(rows):
    return [int(r[0]) for r in rows]


def date(text, name):
    if not text:
        sys.exit(f'Name the day: {name}=YYYY-MM-DD.')
    datetime.date.fromisoformat(text)
    return text


def looked(args):
    if not args.apply:
        print('\nNothing was changed. The same task with -apply does it.')
        sys.exit(0)


def confirm(site, what):
    answer = input(f'{what} Type {site.domain} to go on: ')
    if answer.strip() != site.domain:
        sys.exit('Stopped. Nothing was changed.')


def purge(site, kind, ids):
    """People or groups removed through the API, 500 at a time, waiting for
    each batch to finish."""
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        st, b = site.call('POST', f'{kind}/purge-batch', {'ids': chunk, 'confirm': f'PURGE {len(chunk)}'})
        if st == 200:
            print('  nothing to do: every one is removed or on its way already')
            continue
        if st != 202:
            sys.exit(f'Removing {kind} was refused ({st}): {b[:400].decode()}')
        batch = json.loads(b)
        batch = batch.get('data', batch)
        print(f'  {batch["queued"]} on their way, {batch["skipped"]} skipped')
        started = time.time()
        while True:
            time.sleep(10)
            st, b = site.call('GET', f'{kind}/purge-batch/{batch["batch_id"]}')
            progress = json.loads(b)
            progress = progress.get('data', progress)
            done, failed, total = progress.get('done', 0), progress.get('failed', 0), progress.get('total', 0)
            print(f'  {int(time.time() - started)}s: {done} of {total} done, {failed} failed')
            if done + failed >= total:
                if failed:
                    sys.exit(f'{failed} failed: the same task again tries them again.')
                break


def delete_posts(site, rows):
    """Posts deleted one at a time through the API, as the web app would, so
    that their hashtags, counts and threads are kept right by the services.
    Posts first: a reply under one goes with it, and is then counted as gone."""
    done = {'deleted': 0, 'gone with its thread': 0, 'refused': 0}
    for n, (node, kind) in enumerate(rows, 1):
        st, b = site.call('DELETE', f'{kind}/{node}')
        if st < 300:
            done['deleted'] += 1
        elif st == 404:
            done['gone with its thread'] += 1
        else:
            done['refused'] += 1
            print(f'  {kind}/{node}: refused ({st}) {b[:120].decode(errors="replace")}')
        if n % 100 == 0:
            print(f'  {n} of {len(rows)}')
    print(', '.join(f'{v} {k}' for k, v in done.items()) + '.')


# --- The move.

def task_archive(site, args):
    """The old site's database dump and files, described and proved: the dump
    loaded into a database of its own on the site's MySQL, counted, and
    dropped. Nothing of the site is changed."""
    dump = os.path.abspath(args.dump or '')
    if not os.path.isfile(dump):
        sys.exit('Name the old site\'s database dump: DUMP=<file>.sql or .sql.gz.')
    print(f'The dump: {dump}, {os.path.getsize(dump):,} bytes, sha256 {sha256(dump)}')
    if args.files:
        public = os.path.join(os.path.abspath(args.files), 'assets', 'public')
        if not os.path.isdir(public):
            sys.exit(f'No assets/public in {args.files}: FILES= names the folder that holds the old site\'s assets/.')
        count = size = 0
        for root, _, names in os.walk(public):
            for name in names:
                count += 1
                size += os.path.getsize(os.path.join(root, name))
        print(f'The files: {public}, {count:,} files, {size:,} bytes')
    print('Proving the dump opens, in a database of its own on the site\'s MySQL...')
    site.mysql('DROP DATABASE IF EXISTS php_archive_check; CREATE DATABASE php_archive_check CHARACTER SET utf8mb4;', database='')
    try:
        site.load(dump, 'php_archive_check')
        for table, n in counted(site, 'php_archive_check'):
            print(f'  {table}: {n}')
    finally:
        site.mysql('DROP DATABASE IF EXISTS php_archive_check;', database='')
    print('It opens. Keep the dump and the files where they cannot be changed until the move is done.')


def counted(site, database):
    tables = {r[0] for r in site.mysql('SHOW TABLES;', database=database)}
    found = [t for t in tables if t.endswith('_nodes')] + [t for t in tables if t.endswith('_people_people')]
    if not found:
        sys.exit('The dump has no Anahita PHP tables (…_nodes, …_people_people).')
    return [(t, site.mysql(f'SELECT COUNT(*) FROM `{t}`;', database=database)[0][0]) for t in sorted(found)]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def task_files(site, args):
    """The old site's files into the new site's Garage, then moved to where
    today's Anahita looks for them (anahita-services' s3-migration -from v0).
    The old files stay where they are, and in assets/public/ until tidied."""
    if not args.files:
        sys.exit('Name the folder that holds the old site\'s assets/: FILES=<folder>.')
    public = os.path.join(os.path.abspath(args.files), 'assets', 'public')
    if not os.path.isdir(public):
        sys.exit(f'No assets/public in {args.files}.')
    count = sum(len(n) for _, _, n in os.walk(public))
    print(f'{count:,} files in {public}, to go to s3://{site.bucket}/assets/public/ at files.{site.domain}.')
    looked(args)
    site.s3('sync', public, f's3://{site.bucket}/assets/public/', '--only-show-errors')
    print('Uploaded. Now moved to today\'s layout:')
    s3_migration(site, ['-from', 'v0', '-apply'])
    print('Done. The copies in assets/public/ stay until make files-tidy, after make check.')


def task_files_tidy(site, args):
    """assets/public/ removed, each file only once its copy is in place."""
    s3_migration(site, ['-from', 'v0'] + (['-apply', '-delete-old'] if args.apply else []))
    looked(args)


def s3_migration(site, flags):
    """anahita-services' scripts/s3-migration, at the version the site runs,
    fetched for the purpose. It needs Go."""
    need('go', 's3-migration is written in Go')
    need('git', 'to fetch anahita-services')
    version = re.search(r'newTag: (\S+)', open(os.path.join(site.folder, 'k8s', 'kustomization.yml')).read()).group(1)
    with tempfile.TemporaryDirectory() as work:
        subprocess.run(['git', 'clone', '--quiet', '--depth', '1', '--branch', version,
                        'https://github.com/anahitasocial/anahita-services.git', work], check=True)
        env = dict(os.environ,
                   STORAGE_ENDPOINT=f'https://files.{site.domain}', STORAGE_PATH_STYLE='true',
                   STORAGE_REGION=site.config.get('STORAGE_REGION', 'garage'), STORAGE_BUCKET=site.bucket,
                   STORAGE_ACCESS_KEY=site.secrets.get('STORAGE_ACCESS_KEY', ''),
                   STORAGE_SECRET_KEY=site.secrets.get('STORAGE_SECRET_KEY', ''))
        out = subprocess.run(['go', 'run', '.'] + flags, cwd=os.path.join(work, 'scripts', 's3-migration'), env=env)
        if out.returncode:
            sys.exit('s3-migration failed.')


def task_database(site, args):
    """The new site's database replaced by the old site's, then upgraded by
    the migration job, which finds the PHP tables; then every service started
    again on it."""
    dump = os.path.abspath(args.dump or '')
    if not os.path.isfile(dump):
        sys.exit('Name the old site\'s database dump: DUMP=<file>.sql or .sql.gz.')
    people = site.mysql(f'SELECT COUNT(*) FROM nodes WHERE type = "{PERSON}";')[0][0]
    print(f'{site.domain} has {people} people now. This replaces its whole database with {os.path.basename(dump)}.')
    if int(people) > 1:
        print('More than the first administrator: is this the site you mean? Try it on a site made for trying first.')
    looked(args)
    confirm(site, f'Everything in {site.domain}\'s database goes.')
    site.mysql('DROP DATABASE IF EXISTS anahita; CREATE DATABASE anahita CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;', database='')
    site.load(dump, 'anahita')
    print('Loaded: ' + ', '.join(f'{t} {n}' for t, n in counted(site, 'anahita')))
    print('The migration job is upgrading the PHP tables (make apply in the site\'s folder)...')
    subprocess.run(['make', '-C', site.folder, 'apply'], check=True)
    site.kubectl('wait', '--for=condition=complete', 'job/migration-job', '--timeout=1800s')
    print('\n'.join(site.kubectl('logs', 'job/migration-job').strip().split('\n')[-3:]))
    site.kubectl('rollout', 'restart', 'deployment')
    print('Upgraded; every service started again on it.')
    task_check(site, args)


def task_check(site, args):
    """What there is, and whether it is whole."""
    print('What there is:')
    for t, n in site.mysql('SELECT type, COUNT(*) FROM nodes WHERE purged_at IS NULL AND deleted_at IS NULL '
                           'GROUP BY type ORDER BY type;'):
        print(f'  {int(n):>7}  {t}')
    print('Whether it is whole:')
    for what, n in site.mysql("""
SELECT 'nodes missing an owner', COUNT(*) FROM nodes n
WHERE n.owner_id > 0 AND NOT EXISTS (SELECT 1 FROM nodes o WHERE o.id = n.owner_id)
UNION ALL
SELECT 'nodes missing a parent', COUNT(*) FROM nodes n
WHERE n.parent_id > 0 AND NOT EXISTS (SELECT 1 FROM nodes o WHERE o.id = n.parent_id)
UNION ALL
SELECT 'edges missing an end', COUNT(*) FROM edges e
WHERE NOT EXISTS (SELECT 1 FROM nodes a WHERE a.id = e.node_a_id)
   OR NOT EXISTS (SELECT 1 FROM nodes b WHERE b.id = e.node_b_id)
UNION ALL
SELECT 'photo files named', COUNT(*) FROM photo_files f
JOIN nodes n ON n.id = f.node_id AND n.purged_at IS NULL AND n.deleted_at IS NULL;"""):
        print(f'  {what}: {n}')
    if shutil.which('aws') and site.secrets.get('STORAGE_ACCESS_KEY'):
        listed = site.s3('ls', f's3://{site.bucket}/{PHOTOS}/', '--recursive', capture=True, check=False)
        print(f'  photo files stored, every size: {len(listed.splitlines())}')


# --- Thinning.

def task_inactive(site, args):
    """People who have not visited since a day, and wrote nothing, removed
    with what they own. Administrators, and those named in KEEP, stay."""
    before = date(args.before, 'BEFORE')
    keep = [a.strip().lstrip('@') for a in (args.keep or '').split(',') if a.strip()]
    for alias in keep:
        site.person(alias)
    kept = ' AND p.alias NOT IN (' + ', '.join(f'"{a}"' for a in keep) + ')' if keep else ''
    rows = site.mysql(f'''
SELECT p.id, p.alias, IFNULL(p.last_visited_at, 'never')
FROM nodes p
WHERE p.type = "{PERSON}"
  AND p.purged_at IS NULL
  AND p.person_type = "registered"
  AND (p.last_visited_at IS NULL OR p.last_visited_at < "{before}")
  {kept}
  AND NOT EXISTS (SELECT 1 FROM nodes n
                  WHERE n.created_by = p.id AND n.type LIKE "node.medium.%"
                    AND n.purged_at IS NULL AND n.deleted_at IS NULL)
ORDER BY p.last_visited_at, p.id;''')
    print(f'{len(rows)} people have not visited since {before} and wrote nothing'
          + (f'; kept whatever their last visit: {", ".join("@" + a for a in keep)}' if keep else '') + '.')
    for _, alias, last in rows[:10]:
        print(f'  @{alias}, last visit {last}')
    if len(rows) > 10:
        print(f'  and {len(rows) - 10} more')
    if not rows:
        return
    looked(args)
    site.signin()
    site.keep(f'inactive-before-{before}', ids_of(rows))
    purge(site, 'people', ids_of(rows))


def task_old_posts(site, args):
    """Notes, articles and topics written before a day, by one person (WHO)
    or by everybody, removed with their threads. Photos stay."""
    before = date(args.before, 'BEFORE')
    by = f'AND created_by = {site.person(args.who)}' if args.who else ''
    types = ', '.join(f'"{t}"' for t in KINDS)
    rows = site.mysql(f'''
SELECT id, type, YEAR(created_at), parent_id IS NOT NULL
FROM nodes
WHERE type IN ({types})
  AND created_at < "{before}"
  AND deleted_at IS NULL AND purged_at IS NULL
  {by}
ORDER BY parent_id IS NOT NULL, created_at;''')
    whose = f'@{args.who.lstrip("@")}' if args.who else 'everybody'
    print(f'{len(rows)} notes, articles and topics by {whose} before {before}, replies among them:')
    table = {}
    for _, t, year, reply in rows:
        key = KINDS[t] + (' (replies)' if reply == '1' else '')
        table.setdefault(year, {}).setdefault(key, 0)
        table[year][key] += 1
    for year in sorted(table):
        print(f'  {year}: ' + ', '.join(f'{n} {k}' for k, n in sorted(table[year].items())))
    if not rows:
        return
    looked(args)
    site.signin()
    site.keep(f'posts-before-{before}', ids_of(rows))
    delete_posts(site, [(int(i), KINDS[t]) for i, t, _, _ in rows])


def task_no_author(site, args):
    """Posts whose author is gone, and so are shown by nobody, removed with
    their threads."""
    types = ', '.join(f'"{t}"' for t in KINDS)
    rows = site.mysql(f'''
SELECT n.id, n.type
FROM nodes n
LEFT JOIN nodes a ON a.id = n.created_by
WHERE n.type IN ({types})
  AND n.deleted_at IS NULL AND n.purged_at IS NULL
  AND (a.id IS NULL OR a.purged_at IS NOT NULL)
ORDER BY n.parent_id IS NOT NULL, n.created_at;''')
    print(f'{len(rows)} notes, articles and topics whose author is gone.')
    if not rows:
        return
    looked(args)
    site.signin()
    site.keep('posts-without-author', ids_of(rows))
    delete_posts(site, [(int(i), KINDS[t]) for i, t in rows])


def task_move_photos(site, args):
    """A person's photos moved from a group or a profile (FROM) to their own
    profile (TO): the photos TO posted, unless ALL, which moves every photo.
    Their files are copied first to where the app looks for them, under the
    new owner's folder; the old copies go with make files-tidy or the
    nightly sweep."""
    if not (args.from_ and args.to):
        sys.exit('Name both: FROM=<group or person> TO=<person>.')
    source, _ = site.actor(args.from_)
    target = site.person(args.to)
    target_type = site.mysql(f'SELECT type FROM nodes WHERE id = {target};')[0][0]
    whose = '' if args.all else f'AND created_by = {target}'
    photos = ids_of(site.mysql(f'''
SELECT id
FROM nodes
WHERE type = "{PHOTO}"
  AND owner_id = {source}
  AND purged_at IS NULL AND deleted_at IS NULL
  {whose};'''))
    print(f'{len(photos)} photos to move from @{args.from_.lstrip("@")} to @{args.to.lstrip("@")}'
          + ('' if args.all else f', those @{args.to.lstrip("@")} posted') + '.')
    if not photos:
        return
    stems = {re.sub(r'\.[^.]*$', '', r[0]) for r in site.mysql(
        f'SELECT filename FROM photo_files WHERE node_id IN ({", ".join(map(str, photos))});')}
    listed = site.s3('ls', f's3://{site.bucket}/{PHOTOS}/{source}/', capture=True, check=False).split('\n')
    files = [line.split()[-1] for line in listed if line.strip()]
    files = [f for f in files if re.sub(r'_[^_]*$', '', f) in stems or re.sub(r'\.[^.]*$', '', f) in stems]
    print(f'{len(files)} files of them, every size, to copy to {PHOTOS}/{target}/.')
    looked(args)
    for n, name in enumerate(files, 1):
        site.s3('cp', f's3://{site.bucket}/{PHOTOS}/{source}/{name}', f's3://{site.bucket}/{PHOTOS}/{target}/{name}',
                '--only-show-errors')
        if n % 100 == 0:
            print(f'  {n} of {len(files)} files')
    site.mysql(f'''
UPDATE nodes
SET owner_id = {target}, owner_type = "{target_type}"
WHERE id IN ({", ".join(map(str, photos))});''')
    print(f'Moved {len(photos)} photos, and copied their {len(files)} files.')


def task_groups(site, args):
    """Groups removed with everything in them: those named in GROUPS, or with
    EMPTY, those with no posts. Move out first what is to be kept
    (make move-photos)."""
    if args.groups:
        aliases = [a.strip().lstrip('@') for a in args.groups.split(',') if a.strip()]
        rows = []
        for alias in aliases:
            gid, kind = site.actor(alias)
            if kind != GROUP:
                sys.exit(f'@{alias} is not a group.')
            rows.append((gid, alias))
    elif args.empty:
        rows = [(int(i), a) for i, a in site.mysql(f'''
SELECT g.id, g.alias
FROM nodes g
WHERE g.type = "{GROUP}"
  AND g.purged_at IS NULL
  AND NOT EXISTS (SELECT 1 FROM nodes n
                  WHERE n.owner_id = g.id AND n.type LIKE "node.medium.%"
                    AND n.purged_at IS NULL AND n.deleted_at IS NULL)
ORDER BY g.id;''')]
    else:
        sys.exit('Name them, GROUPS=<group>,<group>, or EMPTY=1 for those with no posts.')
    for gid, alias in rows:
        posts = site.mysql(f'SELECT COUNT(*) FROM nodes WHERE owner_id = {gid} AND type LIKE "node.medium.%" '
                           'AND purged_at IS NULL AND deleted_at IS NULL;')[0][0]
        print(f'  @{alias}: {posts} posts, which go with it')
    print(f'{len(rows)} group{"" if len(rows) == 1 else "s"} to remove.')
    if not rows:
        return
    looked(args)
    site.signin()
    site.keep('groups', [g for g, _ in rows])
    purge(site, 'groups', [g for g, _ in rows])


def task_sweep(site, args):
    """The sweeper once, at once, as it runs every night: hashtags and
    locations no post carries any more, and what was left without an owner."""
    looked(args)
    site.kubectl('delete', 'job', 'migrate-sweep', '--ignore-not-found')
    site.kubectl('create', 'job', 'migrate-sweep', '--from=cronjob/account-sweeper')
    site.kubectl('wait', '--for=condition=complete', 'job/migrate-sweep', '--timeout=900s')
    for line in site.kubectl('logs', 'job/migrate-sweep').strip().split('\n'):
        if 'sweeper:' in line:
            print(' ', line.split('sweeper:', 1)[1].strip())
    site.kubectl('delete', 'job', 'migrate-sweep')


TASKS = {
    'archive': task_archive, 'files': task_files, 'database': task_database, 'check': task_check,
    'files-tidy': task_files_tidy, 'inactive': task_inactive, 'old-posts': task_old_posts,
    'no-author': task_no_author, 'move-photos': task_move_photos, 'groups': task_groups, 'sweep': task_sweep,
}

parser = argparse.ArgumentParser(description='Moves a site from Anahita PHP into a commons site, and thins it.')
parser.add_argument('task', choices=TASKS)
parser.add_argument('--site', required=True, help='the commons folder of the new site')
parser.add_argument('--apply', action='store_true', help='do it; without it, nothing changes')
parser.add_argument('--as', dest='as_', default='', help='the administrator to sign in as, by handle')
parser.add_argument('--dump', default='', help="the old site's database dump, .sql or .sql.gz")
parser.add_argument('--files', default='', help="the folder holding the old site's assets/")
parser.add_argument('--before', default='', help='a day, YYYY-MM-DD')
parser.add_argument('--keep', default='', help='handles kept whatever their last visit, with commas')
parser.add_argument('--who', default='', help='one person, by handle')
parser.add_argument('--from', dest='from_', default='', help='a group or person, by handle')
parser.add_argument('--to', default='', help='a person, by handle')
parser.add_argument('--all', action='store_true', help='move-photos: every photo, not only those TO posted')
parser.add_argument('--groups', default='', help='groups, by handle, with commas')
parser.add_argument('--empty', action='store_true', help='groups: those with no posts')

if __name__ == '__main__':
    arguments = parser.parse_args()
    TASKS[arguments.task](Site(arguments), arguments)
