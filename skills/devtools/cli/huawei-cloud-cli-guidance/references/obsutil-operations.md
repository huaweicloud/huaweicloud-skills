# OBS and obsutil Operations

## Overview

KooCLI exposes Huawei Cloud OBS (Object Storage Service) through two different command families that
use two different parameter systems. This reference explains how the two relate, and documents the
obsutil commands and options that are most often needed for upload, download, listing and
directory synchronization.

Every option listed in this document is taken from the Huawei Cloud obsutil documentation or from
the KooCLI OBS command reference in the repository. Options that could not be verified are
deliberately not listed (see the "Unverified options" section at the end).

## Two ways to use OBS from KooCLI

| Form | Command shape | Help | Parameter style |
|------|---------------|------|-----------------|
| OpenAPI style | `hcloud OBS <operation>` (uppercase service name) | `hcloud OBS --help`, `hcloud OBS <operation> --help` | KooCLI `--param=value` |
| obsutil style (OBS integrated commands) | `hcloud obs <command>` (lowercase) | `hcloud obs help`, `hcloud obs help <command>` | obsutil style, e.g. `-r`, `-limit=10`, `-config=...` |

Relationship between the two forms:

1. KooCLI has integrated the functionality of `obsutil`, the standalone command line tool for
   managing OBS data, so `hcloud obs <command>` can manage OBS buckets and objects without a separate
   obsutil installation.
2. For the OBS integrated commands, the parameters of each command are the same as obsutil's, so the
   option descriptions in this document apply to both `obsutil <command>` and `hcloud obs <command>`.
3. The two forms are separate parameter systems. Always check the matching help output first; do not
   mix `--param=value` options into a `hcloud obs` command.
4. OBS credentials used by `hcloud obs` are **not** inherited from the normal KooCLI profile. The OBS
   module maps to obsutil underneath and needs its own AK/SK and endpoint configuration, stored in the
   obsutil configuration file (`.obsutilconfig`). A typical failure without it is
   `Please set ak, sk and endpoint in the configuration file!` or `InvalidAccessKeyId`.

### When a separate obsutil installation is needed

The built-in `hcloud obs` command set covers the common OBS operations, so a standalone obsutil binary
is not required for them. Install obsutil separately when:

1. The operation you need does not exist in the built-in command set (check `hcloud obs help` and
   `hcloud obs help <command>` first). If it is not found, tell the user to install `obsutil` to get
   the full functionality, and explain why.
2. You need OBS automation that must not depend on KooCLI (for example scheduled backups or scripts
   run on hosts where KooCLI is not installed).
3. You need a newer obsutil version than the one embedded in KooCLI. Compare with
   `hcloud obs version` (shows the embedded obsutil version) and `obsutil version`.
4. Upload features require obsutil **>= 5.5.0**, and file/directory upload must use obsutil, because
   the KooCLI CLI has no object upload (PutObject) command.

obsutil itself is a standalone, small footprint binary (no installation required) for
Windows/Linux/macOS; download it from the official "Download and install obsutil" page.

## Credentials and configuration (safety)

**Never pass AK/SK as plaintext command line arguments and never paste AK/SK into a conversation,
log or shell history.** Prefer the obsutil configuration file, or credentials supplied through your
credential/secret management environment, and rotate credentials regularly.

```bash
# Interactive credential configuration (recommended; writes the obsutil config file)
obsutil config

# Same, through the KooCLI integrated form
hcloud obs config -i=<AK> -k=<SK> -e=obs.<region>.myhuaweicloud.com
```

The command above is shown for completeness of the documented syntax. On a shared machine, prefer the
interactive form so the AK/SK values are not recorded in the shell history.

Default configuration file locations:

- macOS/Linux: `~/.obsutilconfig`
- Windows: `C:\Users\<username>\.obsutilconfig`

Common connection and configuration options (documented on the obsutil command pages):

| Option | Meaning | Note |
|--------|---------|------|
| `-i=xxx` | Specifies the user's AK | Do not use on a command line in plaintext; prefer the config file |
| `-k=xxx` | Specifies the user's SK | Do not use on a command line in plaintext; prefer the config file |
| `-e=xxx` | Specifies the endpoint, e.g. `obs.cn-north-4.myhuaweicloud.com` | Required if it is not already in the config file |
| `-t=xxx` | Specifies the security token | Only for temporary credentials |
| `-config=xxx` | Custom configuration file used for the current command | The config file keys are documented in "Configuration parameter description" (obs_11_0035) |
| `-crr` | Listed in the KooCLI OBS command reference for `config` and for object copy (`cp obs://src obs://dst ... [-crr]`) | Not part of the documented upload/download/sync option sets; check `obsutil help <command>` before use |

## Command map

| Command | Purpose | Documented structure (options omitted for brevity) |
|---------|---------|----------------------------------------------------|
| `ls` | List buckets, or list objects under a bucket/prefix | `obsutil ls [obs://bucket[/prefix]] [...]` |
| `cp` | Upload, download or copy objects, single or recursive | `obsutil cp <source> <destination> [...]` |
| `sync` | Incrementally synchronize a local path with a bucket path | `obsutil sync <source> <destination> [...]` |
| `mb` | Create a bucket | `hcloud obs mb obs://bucket [-fs] [-az=xxx] [-acl=xxx] [-sc=xxx] [-location=xxx] [...]` |
| `stat` | Show bucket or object properties | `hcloud obs stat obs://bucket[/key] [-acl] [-bf=xxx] [...]` |
| `rm` | Delete a bucket (must be empty) or delete objects | `hcloud obs rm obs://bucket [-f]`, `hcloud obs rm obs://bucket[/key] -r [-f] [...]` |
| `help` | Show the tool's OBS commands, or the help of one command | `obsutil help [command]`, `hcloud obs help [command]` |

Additional documented commands include `mkdir`, `mv`, `chattri`, `bucketpolicy`, `sign`, `restore`,
`abort`, `create-share`, `share-ls`, `share-cp`, `clear`, `archive`, `version` and
`ls -failed` (list failed-task report files produced by `cp` and `sync`).

## Listing buckets and objects (`obsutil ls`)

Documented structure for objects:

```bash
obsutil ls obs://bucket[/prefix] [-s] [-fs] [-d] [-v] [-du] [-marker=xxx] [-versionIdMarker=xxx] \
  [-encoding-type=url] [-bf=xxx] [-limit=1] [-format=default] \
  [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]
```

Documented structure for buckets (KooCLI OBS command reference):

```bash
hcloud obs ls [-s] [-du] [-sc] [-j=1] [-limit=1] [-format=default] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]
```

| Option | Meaning |
|--------|---------|
| `-s` | Concise format: results contain only the object name (for buckets, a bucket name list) |
| `-d` | List only objects and sub-directories directly under the current "directory" instead of recursing |
| `-v` | List multiple object versions (latest plus historical versions) |
| `-du` | Return the total size of the listed objects quickly, without object details |
| `-limit=n` | Maximum number of results; `<= 0` means all results; default is 1000 for object listing |
| `-marker=xxx` | Start position of the listing; together with `-versionIdMarker` it continues a paged listing |
| `-bf=xxx` | Byte display format: `human-readable` or `raw` |
| `-format=default` | Print each listing result on one line |

Notes:

- Bucket listing and object listing share the same `ls` command; passing an `obs://bucket` argument
  lists that bucket, while `obsutil ls` with no bucket argument lists buckets. The official
  documentation shows the bucket form in interactive mode as `ls -limit=3 -s`, printing
  `Bucket number: 3`.
- When a bucket holds many objects, use `-limit` and continue with the returned `Next marker`
  instead of listing everything at once.

## Uploading objects (`obsutil cp`)

```bash
# Single file
obsutil cp file_url obs://bucket[/key] [-arcDir=xxx] [-dryRun] [-link] [-u] [-vlength] [-vmd5] \
  [-p=1] [-threshold=52428800] [-acl=xxx] [-sc=xxx] [-meta=aaa:bbb#ccc:ddd] [-ps=auto] \
  [-cpd=xxx] [-fr] [-o=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]

# Folder (recursive)
obsutil cp folder_url obs://bucket[/key] -r [-arcDir=xxx] [-dryRun] [-link] [-f] [-flat] [-u] \
  [-j=1] [-p=1] [-threshold=52428800] [-acl=xxx] [-sc=xxx] [-include=*.xxx] [-exclude=*.xxx] \
  [-timeRange=time1-time2] [-mf] [-o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]
```

| Option | Meaning |
|--------|---------|
| `-r` | Recursively upload all files and sub-folders. **Required** when uploading a folder |
| `-f` | Force the operation, do not ask for confirmation prompts |
| `-flat` | Upload only the contents of the folder, without the folder itself as an object |
| `-u` | Incremental upload: upload only when the object is missing, its size differs, or its last modification time is older than the local file |
| `-acl=xxx` | Predefined object access policy: `private`, `public-read`, `public-read-write`, `bucket-owner-full-control` |
| `-sc=xxx` | Storage class: `standard`, `warm`, `cold`, `deep-archive` |
| `-arcDir=xxx` | Archive directory: successfully uploaded files are moved to this local path |
| `-include=*.xxx` / `-exclude=*.xxx` | Name matching filters; excludes are evaluated before includes |
| `-timeRange=time1-time2` | Match by last modification time, format `yyyyMMddHHmmss` (UTC) |
| `-j=1` | Maximum number of parallel batch tasks (folder upload) |
| `-p=1` | Maximum number of parallel parts for one multipart upload |
| `-threshold=...` | Size threshold in bytes that starts multipart upload; accepts units such as `1MB` |
| `-vlength` / `-vmd5` | Verify the uploaded object length / MD5 after upload |
| `-cpd=xxx` | Directory for checkpoint files (default `~/.obsutil_checkpoint`) |
| `-o=xxx` | Directory for result list files (default `~/.obsutil_output`) |
| `-dryRun` | Run in test mode without uploading |

Behaviour notes:

- Uploaded file size limits: at least 0 bytes; up to 5 GB without multipart upload and up to
  48.8 TB with multipart upload.
- `-u` produces one HEAD request per compared file, which is billed.
- The object key rules depend on the target value: an empty `key` uploads to the bucket root using the
  local file/folder name; a `key` ending with `/` uploads into that prefix; otherwise, for a file the
  key becomes the file name, and for a folder the objects go under `key/`.

## Downloading objects (`obsutil cp`)

```bash
# Single object
obsutil cp obs://bucket/key file_or_folder_url [-tempFileDir=xxx] [-dryRun] [-u] [-vlength] [-vmd5] \
  [-p=1] [-threshold=52428800] [-versionId=xxx] [-ps=auto] [-cpd=xxx] [-fr] [-o=xxx] \
  [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]

# Batch download by object name prefix
obsutil cp obs://bucket[/key] folder_url -r [-tempFileDir=xxx] [-dryRun] [-f] [-flat] [-u] \
  [-j=1] [-p=1] [-threshold=52428800] [-include=*.xxx] [-exclude=*.xxx] [-timeRange=time1-time2] \
  [-mf] [-o=xxx] [-cpd=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]
```

- `-r` is required for prefix-based batch download. `-f` (force, no prompt) is documented for the
  batch form; the single-object form does not document `-f`.
- `-u` performs incremental download: download only when the local file is missing, its size differs,
  or it is older than the object.
- `-flat` omits the parent object prefix when writing local files during a batch download.
- `-tempFileDir=xxx` holds temporary files of a multipart download; it must be writable and large
  enough for the object. Objects in the infrequent access storage class must be restored before they
  can be downloaded.

## Directory synchronization (`obsutil sync`)

```bash
# Sync a local path up to a bucket path
obsutil sync file_url obs://bucket[/key] [...]
obsutil sync folder_url obs://bucket[/key] [-arcDir=xxx] [-dryRun] [-link] [-vlength] [-vmd5] \
  [-j=1] [-p=1] [-threshold=52428800] [-acl=xxx] [-sc=xxx] [-meta=aaa:bbb#ccc:ddd] [-ps=auto] \
  [-include=*.xxx] [-exclude=*.xxx] [-timeRange=time1-time2] [-at] [-mf] [-o=xxx] [-cpd=xxx] \
  [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]
```

`sync` is already incremental: each source file is compared with the corresponding target object and
only changed sources are uploaded, so no `-u` or `-r` flag is needed (and none is documented).
Comparison produces one HEAD request per file, which is billed.

Documented options specific to `sync`:

| Option | Meaning |
|--------|---------|
| `-j=1` | Maximum number of parallel batch tasks when syncing a folder |
| `-arcDir=xxx` | Archive directory for successfully synced local files |
| `-include` / `-exclude` / `-timeRange` / `-at` / `-mf` | Same name/time filters as `cp`; `-at` matches last access time together with `-timeRange` |
| `-acl`, `-sc`, `-meta`, `-ps`, `-p`, `-threshold`, `-vlength`, `-vmd5`, `-cpd`, `-o`, `-dryRun` | Same meaning as for `cp` |

There is also an object-to-object sync (bucket to bucket). Non-documented flags must not be assumed:
check `obsutil help sync` (or `hcloud obs help sync`) for the option set of the installed version.

## Bucket operations (`mb`, `stat`, `rm`)

```bash
# Create a bucket
hcloud obs mb obs://bucket [-fs] [-az=xxx] [-acl=xxx] [-sc=xxx] [-location=xxx] \
  [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]

# Bucket properties (storage class, region, versioning, object count, used capacity, quota, ...)
hcloud obs stat obs://bucket [-acl] [-bf=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-t=xxx]

# Delete an empty bucket
hcloud obs rm obs://bucket [-f] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]

# Delete objects by prefix (recursive)
hcloud obs rm obs://bucket[/key] -r [-j=1] [-f] [-v] [-o=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]

# Delete a single object
hcloud obs rm obs://bucket/key [-f] [-versionId=xxx] [-fr] [-o=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]
```

- `-location=xxx` selects the region (`cn-north-4`, `cn-east-3`, ...) and is fixed after creation.
- `-sc=xxx` sets the default storage class: `standard`, `warm`, `cold`, `deep-archive`.
- `-az=xxx` sets the availability zone (for example `multi-az`). `-fs` is a documented `mb` flag for
  file system buckets; confirm its exact effect in your version with `hcloud obs help mb` before
  using it.
- **Deletion is irreversible.** A bucket can only be deleted when it is empty (no objects, historical
  versions or incomplete multipart uploads). Deleting a bucket, deleting objects and recursive
  deletion destroy data permanently; confirm the exact `obs://bucket/key` scope before running them,
  and prefer listing the scope with `ls` first.

## Object properties and archived objects

```bash
# Object properties (metadata, storage class, ...)
hcloud obs stat obs://bucket/key [-acl] [-bf=xxx] [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-t=xxx]

# Restore an archived (cold) object, and batch restore a prefix
hcloud obs restore obs://bucket/key [-d=1] [-t=xxx] [-versionId=xxx] [-fr] [-o=xxx] \
  [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-token=xxx]
hcloud obs restore obs://bucket[/key] -r [-f] [-v] [-d=1] [-o=xxx] [-j=1] \
  [-config=xxx] [-e=xxx] [-i=xxx] [-k=xxx] [-token=xxx]
```

`-d=1` is the number of days for which the restored copy stays readable. `stat` is also the reliable
way to read exact object count/size for one bucket, or to check the bucket file-interface type before
attaching it to a service.

### About "archive" options

There is no documented `-arc` option. Archive behaviour is controlled by:

- `-sc=cold` / `-sc=deep-archive` — store new objects in an archive storage class;
- `-arcDir=xxx` — local archive directory for successfully uploaded/synced files;
- `hcloud obs restore ... -d=<days>` — restore an archived object so it can be downloaded;
- `ls ... -v` and `stat ...` — inspect storage class and version/deletion markers.

## Copy-paste examples

All examples are complete commands. Replace the bucket name (bucket names are globally unique) and
the paths with your own values; credentials come from the obsutil configuration file.

```bash
# 1) List buckets, then list objects under a prefix with a size limit
obsutil ls -limit=100
obsutil ls obs://example-bucket/reports/ -limit=50 -d

# 2) Upload an entire folder recursively, incremental, forcing prompts off
#    Linux / macOS
obsutil cp /data/reports/ obs://example-bucket/reports/ -r -f -u
#    Windows
obsutil cp d:\data\reports obs://example-bucket/reports -r -f -u

# 3) Upload a single file and make it publicly readable
obsutil cp /data/reports/2026-01.tar.gz obs://example-bucket/reports/2026-01.tar.gz -acl=public-read

# 4) Download a single object and a whole prefix
obsutil cp obs://example-bucket/reports/2026-01.tar.gz /data/restore/
obsutil cp obs://example-bucket/reports/2026/ /data/reports-2026/ -r -f -u

# 5) Synchronize a local archive directory to a bucket, excluding temporary files
obsutil sync /data/archive/ obs://example-bucket/archive/ -j=5 -exclude='*.tmp'

# 6) Create a bucket, check it, and list its objects with total size
hcloud obs mb obs://example-bucket -sc=standard -location=cn-north-4
hcloud obs stat obs://example-bucket
obsutil ls obs://example-bucket/ -du

# 7) Check the help of the two command families (always do this first)
hcloud obs help
hcloud obs help cp
obsutil help cp
```

## Notes

- obsutil style commands use a **single** leading dash for every option (`-r`, `-f`, `-acl=private`,
  `-limit=10`, `-config=...`). The KooCLI `--param=value` rule (double dash) applies to the
  cloud-service API commands such as `hcloud CES ShowMetricData`, not to `obsutil` / `hcloud obs`.
- Prefer `-dryRun` where it is documented, and list the target prefix before any
  destructive command.
- `-f` means "do not prompt", not "overwrite silently with different content": for uploads the object
  is replaced by default, and `-u` is what makes repeated runs incremental.
- Result list files from batched `cp`/`sync` runs are written under `-o` (default
  `~/.obsutil_output`); failed tasks can be inspected there and with `obsutil ls -failed`.
- If `hcloud obs help`/`obsutil ...` fails while reading the configuration file (for example
  `open C:\Users\<user>\.obsutilconfig: Access is denied.`), the current process cannot read the
  obsutil configuration file. Fix file permissions or pass an accessible file with `-config=xxx`;
  do not work around it by putting AK/SK on the command line.

## Unverified options

The following are sometimes assumed but are **not** documented in the sources used for this
reference, therefore they are not presented as valid options:

- `-arc` (archive) — not documented; use `-sc`, `-arcDir` and `restore -d=<days>` as described above.
- `-delete` for `sync` — not documented in the `sync` structures; `sync` does not remove target
  objects that are missing locally.
- `-bucket` for `rm` — the documented bucket deletion form is `rm obs://bucket`; the `-bucket` form
  used by some scripts was not verified.

Always confirm the option set of the installed version with `obsutil help <command>` (or
`hcloud obs help <command>`) before relying on a flag.

## Sources

- [obsutil introduction (obs_11_0001)](https://support.huaweicloud.com/utiltg-obs/obs_11_0001.html)
- [Upload objects (obs_11_0013)](https://support.huaweicloud.com/utiltg-obs/obs_11_0013.html)
- [List objects (obs_11_0014)](https://support.huaweicloud.com/utiltg-obs/obs_11_0014.html)
- [Download objects (obs_11_0018)](https://support.huaweicloud.com/utiltg-obs/obs_11_0018.html)
- [Incremental sync upload of objects (obs_11_0042)](https://support.huaweicloud.com/utiltg-obs/obs_11_0042.html)
- [Download and install obsutil (obs_11_0003)](https://support.huaweicloud.com/utiltg-obs/obs_11_0003.html)
- Configuration parameter description (obs_11_0035), the page referenced by the command pages above
  for the keys accepted by `-config`: <https://support.huaweicloud.com/utiltg-obs/obs_11_0035.html>
- Official pages listed by the obsutil command tables for the commands whose structures are quoted
  from the KooCLI OBS command reference in this repository:
  [create bucket (obs_11_0008)](https://support.huaweicloud.com/utiltg-obs/obs_11_0008.html),
  [list buckets (obs_11_0009)](https://support.huaweicloud.com/utiltg-obs/obs_11_0009.html),
  [bucket properties (obs_11_0010)](https://support.huaweicloud.com/utiltg-obs/obs_11_0010.html),
  [delete bucket (obs_11_0011)](https://support.huaweicloud.com/utiltg-obs/obs_11_0011.html),
  [object properties (obs_11_0015)](https://support.huaweicloud.com/utiltg-obs/obs_11_0015.html),
  [restore archived objects (obs_11_0016)](https://support.huaweicloud.com/utiltg-obs/obs_11_0016.html),
  [delete objects (obs_11_0021)](https://support.huaweicloud.com/utiltg-obs/obs_11_0021.html),
  [incremental sync download (obs_11_0043)](https://support.huaweicloud.com/utiltg-obs/obs_11_0043.html)
- In-repo cross-checks: `skills/storage/obs/huawei-cloud-obs-upload/` (`SKILL.md`,
  `references/troubleshooting.md`, `references/task-upload-file.md`,
  `references/task-scheduled-upload.md`, `references/related-apis.md`),
  `skills/storage/obs/huawei-cloud-obs-website-host/references/cli-installation-guide.md`,
  `skills/storage/obs/huawei-cloud-obs-bucket-create/SKILL.md`,
  `skills/storage/obs/huawei-cloud-obs-lifecycle-management/SKILL.md`,
  and the KooCLI OBS command reference under
  `skills/solution/ops/huawei-cloud-solution-ops/materials/hcloud-docs-md/`.
