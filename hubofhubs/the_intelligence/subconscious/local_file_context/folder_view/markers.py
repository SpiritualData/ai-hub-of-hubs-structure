"""The data of folder judgment: one row per kind of folder or file that is not worth scanning, for any programming language and tool.

A new ecosystem is one more row here and no code. Matching is by the rules of ``judgment.py``:

* ``names`` are case-insensitive name patterns (``fnmatch``) of a folder or a file.
* ``beside`` are entries that must sit in the PARENT folder (a project file that proves the name is the tool's output and not a folder of the
  same name that holds work), and ``inside`` are entries that must sit in the folder itself. Either list is "any of"; an item written
  ``a+b`` needs both. When a row has both lists empty, the name alone is the evidence (``node_modules`` is nothing else).
* ``kind`` groups the reason: dependency, build, cache, vcs, generated, binary, scratch, risky.
* ``risky`` rows (credentials, backups, other people's private data) are never read into a view unasked; the rest are merely unlikely to help.

Standard library only; importing this module runs nothing.
"""
from __future__ import annotations

from typing import NamedTuple, Tuple


class Marker(NamedTuple):
    kind: str
    names: Tuple[str, ...]
    reason: str
    beside: Tuple[str, ...] = ()
    inside: Tuple[str, ...] = ()
    risky: bool = False


# Project files that prove a folder next to them is a build or dependency folder of that project (any language and tool).
PROJECT_FILES = ("package.json", "pyproject.toml", "setup.py", "setup.cfg", "Makefile", "makefile", "CMakeLists.txt", "build.gradle", "build.gradle.kts",
                 "settings.gradle", "settings.gradle.kts", "pom.xml", "build.sbt", "Cargo.toml", "go.mod", "mix.exs", "Gemfile", "composer.json",
                 "pubspec.yaml", "*.csproj", "*.fsproj", "*.vbproj", "*.sln", "tsconfig.json", "Package.swift", "deno.json", "Rakefile",
                 "meson.build", "WORKSPACE", "BUILD.bazel", "build.xml", "project.clj", "stack.yaml", "*.cabal", "dune-project", "rebar.config",
                 "Podfile", "Cartfile", "elm.json", "angular.json", "next.config.js", "vite.config.*", "webpack.config.*", "build.zig", "Dockerfile")
DOTNET_FILES = ("*.csproj", "*.fsproj", "*.vbproj", "*.sln")

FOLDERS: Tuple[Marker, ...] = (
    # dependencies: other people's code that a tool installed
    Marker("dependency", ("node_modules", "bower_components", "jspm_packages", "web_modules"), "installed JavaScript packages"),
    Marker("dependency", ("site-packages", "dist-packages", "__pypackages__"), "installed Python packages"),
    Marker("dependency", ("vendor",), "vendored dependencies", beside=("go.mod", "composer.json", "Gemfile", "Cargo.toml", "vendor.json", "glide.yaml"),
           inside=("modules.txt", "autoload.php", "bundle", "ruby")),
    Marker("dependency", (".bundle",), "Ruby bundler settings and gems"),
    Marker("dependency", ("Pods", "Carthage"), "installed iOS dependencies", beside=("Podfile", "Cartfile"), inside=("Manifest.lock", "Build")),
    Marker("dependency", ("packages",), "NuGet packages", beside=("packages.config", "*.sln", "NuGet.config", "nuget.config"), inside=("repositories.config",)),
    Marker("dependency", ("pkg",), "Go module cache", inside=("mod/cache",)),
    Marker("dependency", ("mod",), "Go module cache", inside=("cache/download",)),
    Marker("dependency", ("registry",), "Cargo registry cache", inside=("index+src", "cache+src")),
    Marker("dependency", (".cargo", ".rustup", ".m2", ".ivy2", ".sbt", ".nuget", ".npm", ".yarn", ".pnpm-store", ".cpan", ".cabal", ".stack",
                          ".pub-cache", ".conda", ".gem", ".composer", ".nvm", ".pyenv", ".rbenv", ".asdf"), "a package manager's home and downloads"),
    Marker("dependency", ("elm-stuff", ".stack-work", "dist-newstyle", ".dart_tool", ".pio", "Godeps", "_vendor"), "a tool's installed dependencies"),
    Marker("dependency", ("deps",), "Elixir dependencies", beside=("mix.exs",)),
    Marker("dependency", ("lib",), "installed library folder of an environment", inside=("python*", "site-packages")),
    # build output: generated from sources that sit elsewhere
    Marker("build", ("build", "dist", "out", "output"), "build output", beside=PROJECT_FILES),
    Marker("build", ("target",), "build output", beside=("Cargo.toml", "pom.xml", "build.sbt", "build.gradle", "build.gradle.kts", "Cargo.lock"),
           inside=(".rustc_info.json", "CACHEDIR.TAG", "classes", "debug+release")),
    Marker("build", ("bin", "obj", "Debug", "Release", "x64", "x86"), "compiled output", beside=DOTNET_FILES + ("*.vcxproj",)),
    Marker("build", ("_build",), "build output", beside=("mix.exs", "dune-project", "rebar.config", "conf.py", "Makefile")),
    Marker("build", ("site",), "generated site", beside=("mkdocs.yml", "mkdocs.yaml")),
    Marker("build", ("_site",), "generated site", beside=("_config.yml", "_config.yaml")),
    Marker("build", ("public",), "generated site", beside=("config.toml", "hugo.toml", "gatsby-config.js", "gatsby-config.ts")),
    Marker("build", (".next", ".nuxt", ".svelte-kit", ".angular", ".astro", ".docusaurus", ".vercel", ".output", ".turbo", ".parcel-cache",
                     ".expo", ".serverless", ".gradle", ".build", ".swiftpm", "DerivedData", "cmake-build-*", ".webpack", ".cxx", ".externalNativeBuild"),
           "build output and tool state"),
    Marker("build", ("*.egg-info", ".eggs", "*.dist-info", "*.xcframework", "*.app", "*.dSYM"), "packaging output"),
    # caches and tool state
    Marker("cache", ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".pytype", ".pyre", ".tox", ".nox", ".hypothesis", ".cache",
                     ".ipynb_checkpoints", ".sass-cache", ".eslintcache", ".nyc_output", "htmlcov", ".terraform", ".terragrunt-cache",
                     ".vagrant", ".idea", ".vscode", ".vs", ".history", ".fleet", ".eclipse", ".settings", "__MACOSX", ".Trash*", ".Spotlight-V100",
                     ".fseventsd", ".DS_Store"), "a cache or a tool's own state"),
    Marker("cache", ("coverage",), "coverage output", inside=("lcov.info", "coverage-final.json", "clover.xml", "lcov-report", "cobertura*.xml")),
    Marker("cache", ("logs", "log"), "log output", inside=("*.log", "*.log.*")),
    Marker("scratch", ("tmp", "temp", ".tmp", ".temp"), "temporary files"),
    # version control internals
    Marker("vcs", (".git", ".hg", ".svn", ".bzr", "CVS", "_darcs", ".fossil", ".jj"), "version control internals"),
    # risky: credentials and secrets
    Marker("risky", ("credentials", "credential", "secrets", "secret", ".secrets", "private_keys", "private-keys", "keystore", "keystores", "passwords",
                     "password-store", ".password-store", ".vault", "vault-keys"), "holds credentials or secrets", risky=True),
    Marker("risky", (".ssh", ".aws", ".gnupg", ".gpg", ".kube", ".azure", ".gcloud", ".docker", ".config/gcloud", ".oci", ".terraform.d", ".mozilla",
                     ".thunderbird", ".keychain"), "holds a person's keys, tokens or login state", risky=True),
    # risky: backups and archives (old copies of data nobody meant to share)
    Marker("risky", ("backup", "backups", ".backup", ".backups", "bak", "archive", "archives", "archived", "snapshots", "dumps", "db_dumps", ".Trash",
                     "trash", "recycle", "$RECYCLE.BIN", "old_backups"), "holds backups or archives", risky=True),
    # risky: other people's private data
    Marker("risky", ("private", "personal", "maildir", "mailbox", "mail", "medical", "payroll", "pii", "personnel", "health_records"),
           "may hold other people's private data", risky=True),
)

# Entries that, found directly inside a folder, show that the folder holds credentials or secrets whatever its name is.
SECRET_FILES: Tuple[str, ...] = (
    ".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore", "*.kdbx", "*.ppk", "id_rsa", "id_rsa.*", "id_dsa",
    "id_ecdsa", "id_ed25519", "id_ed25519_*", ".netrc", "_netrc", ".npmrc", ".pypirc", ".htpasswd", ".git-credentials", ".pgpass", ".my.cnf",
    "credentials", "credentials.*", "client_secret*.json", "client_secrets*.json", "service-account*.json", "service_account*.json",
    "serviceaccount*.json", "*-credentials.json", "*_credentials.json", "secrets.*", "secrets", "*.tfstate", "*.tfstate.backup", "*.tfvars",
    "terraform.tfvars", "authorized_keys", "known_hosts", "*.gpg", "*.asc", "*.keychain", "*.keychain-db", "master.key", "vault.yml", "wallet.dat")
# Of those, the ones that on their own do not make the folder risky: a project folder keeps its own .env or .npmrc beside its work, and only that file is
# left out. A key store (a key, a certificate, a keychain, service-account JSON) makes the whole folder risky.
FILE_ONLY_SECRETS: Tuple[str, ...] = (".env", ".env.*", "*.env", ".npmrc", ".pypirc", ".netrc", "_netrc", ".htpasswd", ".git-credentials", ".pgpass", ".my.cnf",
                                      "*.tfvars", "terraform.tfvars", "secrets.*", "secrets", "vault.yml", "known_hosts")
# A secrets file that is meant to be shared (a template with no value).
SECRET_TEMPLATES: Tuple[str, ...] = (".env.example", ".env.sample", ".env.template", ".env.dist", "*.env.example", "*.pub", "*.example", "*.sample",
                                     "*.template", "*.md", "*.txt.example")

# Files that are other people's backups or partial copies.
BACKUP_FILES: Tuple[str, ...] = ("*.bak", "*.backup", "*.old", "*.orig", "*.rej", "*.swp", "*.swo", "*~", "*.sql.gz", "*.dump", "*.mbox", "*.pst", "*.ost")

# Files that are generated bulk: a tool wrote them and nobody reads them for work.
GENERATED_FILES: Tuple[str, ...] = (
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "Cargo.lock", "poetry.lock", "Pipfile.lock", "uv.lock",
    "pdm.lock", "composer.lock", "Gemfile.lock", "go.sum", "packages.lock.json", "mix.lock", "pubspec.lock", "Podfile.lock", "Package.resolved",
    "gradle.lockfile", "flake.lock", "conan.lock", "*.min.js", "*.min.css", "*.min.map", "*.map", "*.bundle.js", "*.chunk.js", "*.pb.go", "*_pb2.py",
    "*.generated.*", "*.designer.cs", ".DS_Store", "Thumbs.db")

# Files that are binary or media: their text cannot be read as work.
BINARY_SUFFIXES = frozenset(
    ".pyc .pyo .class .o .obj .a .lib .so .dll .dylib .exe .bin .wasm .jar .war .ear .whl .egg .nupkg .gem .deb .rpm .apk .ipa .dex .pdb .beam "
    ".png .jpg .jpeg .gif .bmp .ico .webp .tif .tiff .heic .psd .ai .raw .svgz .mp3 .wav .flac .ogg .m4a .aac .mp4 .mov .avi .mkv .webm .wmv "
    ".woff .woff2 .ttf .otf .eot .zip .tar .tgz .gz .bz2 .xz .7z .rar .zst .iso .dmg .img .vhd .vmdk .pdf .docx .xlsx .pptx .odt .ods .epub "
    ".sqlite .sqlite3 .db .mdb .parquet .feather .arrow .npy .npz .pkl .pickle .h5 .hdf5 .onnx .pt .pth .ckpt .safetensors .tflite .mat".split())

# Text formats that become bulk dumps when large (a data export, a log, a database dump).
DATA_SUFFIXES = frozenset(".csv .tsv .json .jsonl .ndjson .xml .sql .log .dat .ldif .geojson .yaml .yml".split())
DATA_BYTES = 100_000

# What a file's own opening shows is a credential, in any file of a type that can hold one.
SECRET_CONTENT = (
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\"private_key\"\s*:\s*\"-----BEGIN", r"\bAKIA[0-9A-Z]{16}\b", r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    r"\bxox[abpr]-[A-Za-z0-9-]{20,}\b", r"\bsk-[A-Za-z0-9]{32,}\b",
)
SETTING_SUFFIXES = frozenset(".env .ini .cfg .conf .properties .toml .yaml .yml .json".split())
SECRET_SETTING = r"(?im)^\s*[\"']?[\w.-]*(?:password|passwd|secret|token|api[_-]?key|access[_-]?key)[\w.-]*[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+_=.-]{12,}"

# Suffixes of files that are code or prose even when their name looks like a secrets file (``credentials.py`` reads credentials, it holds none).
NOT_SECRET_SUFFIXES = frozenset(".py .js .ts .tsx .jsx .go .rs .java .kt .rb .cs .php .swift .c .h .cpp .md .rst .html .css .pyc".split())
