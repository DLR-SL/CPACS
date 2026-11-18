"""The changes of the schema since the last CPACS release, drawn on the diagram.

    pixi run doc-diff                    # build/diff/diff.html (+ report.md, summary.md, diff.json)
    pixi run doc-diff --open             # and open it in the browser
    pixi run doc-diff --base v3.5        # against another release, branch or commit

The `Build documentation` workflow runs it with `-o build/doc/diff --link-from
build/doc/index.html`, which also puts a link to the diff on the start page of the site.

Rename decisions (which removed node became which added one) are read by cpacs-doc from
`cpacs_schema.renames.toml` next to the schema, if there is one.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

CPACS = "https://github.com/DLR-SL/CPACS"
SCHEMA = Path("schema/cpacs_schema.xsd")
# The start page of the site links the documentation with this line; the diff link goes after it.
DOC_LINK = '<p><a href="doc/index.html">Documentation</a></p>'
RELEASE = re.compile(r"v(\d+)\.(\d+)(?:\.(\d+))?")


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def last_release() -> str:
    """The highest release tag vX.Y[.Z] of the CPACS repository (no release candidates)."""
    tags = [line.rsplit("/", 1)[-1] for line in git("ls-remote", "--tags", "--refs", CPACS, "v*").splitlines()]
    releases = [t for t in tags if RELEASE.fullmatch(t)]
    if not releases:
        raise SystemExit(f"no release tag found in {CPACS}")
    return max(releases, key=lambda t: tuple(int(x or 0) for x in RELEASE.fullmatch(t).groups()))


def fetch_base(ref: str, cache: Path) -> tuple[Path, str]:
    """The schema at `ref`, fetched into build/base/. A release or a commit id is fetched once,
    a branch every time. Returns the file and the short commit id."""
    fixed = RELEASE.fullmatch(ref) or re.fullmatch(r"[0-9a-f]{40}", ref)
    out = cache / re.sub(r"[^A-Za-z0-9.-]+", "_", ref) / "cpacs_schema.xsd"
    sha_file = out.with_suffix(".sha")
    if fixed and out.exists() and sha_file.exists():
        return out, sha_file.read_text(encoding="utf-8").strip()
    repo = cache / "repo"
    if not (repo / ".git").exists():
        repo.mkdir(parents=True, exist_ok=True)
        git("init", "-q", cwd=repo)
    git("fetch", "-q", "--depth", "1", CPACS, ref, cwd=repo)
    sha = git("rev-parse", "--short=7", "FETCH_HEAD", cwd=repo)
    content = subprocess.run(["git", "show", f"FETCH_HEAD:{SCHEMA.as_posix()}"], cwd=repo, check=True,
                             capture_output=True).stdout
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(content)
    sha_file.write_text(sha, encoding="utf-8")
    return out, sha


def base_label(ref: str, sha: str) -> str:
    m = RELEASE.fullmatch(ref)
    return f"CPACS {ref[1:]}" if m else f"{ref}@{sha}"


def own_label() -> str:
    branch = os.environ.get("GITHUB_REF_NAME") or git("rev-parse", "--abbrev-ref", "HEAD")
    sha = (os.environ.get("GITHUB_SHA") or git("rev-parse", "HEAD"))[:7]
    changed = not os.environ.get("CI") and git("status", "--porcelain", "--", str(SCHEMA.parent))
    return f"{branch}@{sha}" + (" + local changes" if changed else "")


def link_from(index: Path, target: Path, text: str) -> None:
    page = index.read_text(encoding="utf-8")
    if DOC_LINK not in page:
        print(f"note: no documentation link in {index}; the diff is not linked from it", file=sys.stderr)
        return
    href = Path(os.path.relpath(target, index.parent)).as_posix()
    page = page.replace(DOC_LINK, f'{DOC_LINK}<p><a href="{href}">{text}</a></p>', 1)
    index.write_text(page, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", help="release tag, branch or commit to compare with (default: the last release)")
    ap.add_argument("-o", "--output", type=Path, default=Path("build/diff"))
    ap.add_argument("--link-from", type=Path, help="start page of the site that gets a link to the diff")
    ap.add_argument("--open", action="store_true", help="open the diff in the browser")
    args = ap.parse_args()

    ref = args.base or last_release()
    base, sha = fetch_base(ref, Path("build/base"))
    old_label = base_label(ref, sha)
    result = subprocess.run([sys.executable, "-m", "cpacs_doc", "diff", str(base), str(SCHEMA),
                             "-o", str(args.output), "--old-label", old_label, "--new-label", own_label()])
    if result.returncode:
        return result.returncode
    page = args.output / "diff.html"
    if args.link_from:
        link_from(args.link_from, page, f"Changes since {old_label}")
    if args.open:
        webbrowser.open(page.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
