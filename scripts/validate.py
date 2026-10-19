#!/usr/bin/env python3
"""Check the portable skill and build a minimal, reproducible release archive."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "overseas-radar-b2b-research"
SKILL = ROOT / "skills" / NAME
VERSION = "0.1.0"
FIELDS = "sample_id object_name claim source_url source_nature content_nature published_at accessed_at retrieval_mode market currency price price_basis quantity_variant specification customization delivery_terms verification_status supported_scope limitations buyer_role purchase_intent_status next_verification client_visible internal_note".split()


def check():
    errors = []
    required = ["SKILL.md", "agents/openai.yaml", "references/evidence-schema.md",
                "references/evidence-register.csv", "references/report-template.md",
                "references/worked-example.md", "references/example-evidence.csv",
                "references/host-adaptation.md"]
    for item in required:
        if not (SKILL / item).is_file():
            errors.append(f"Missing skill resource: {item}")
    if errors:
        return errors, []
    body = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    header = re.match(r"\A---\n(.*?)\n---\n", body, re.S)
    if not header or f"name: {NAME}" not in header.group(1) or "description:" not in header.group(1):
        errors.append("Invalid skill frontmatter")
    if not header or f'version: "{VERSION}"' not in header.group(1):
        errors.append("Skill version differs from package version")

    paths = sorted(p for p in SKILL.rglob("*") if p.is_file())
    if any(p.is_symlink() or p.suffix not in {".md", ".yaml", ".csv"} for p in paths):
        errors.append("Skill contains symlinks or unexpected file types")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if "[TODO:" in text:
            errors.append(f"Unfinished scaffold: {path.relative_to(ROOT)}")
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", text):
                if re.match(r"(?:https?://|mailto:|#)", target):
                    continue
                dest = (path.parent / target.split("#")[0]).resolve()
                if not dest.is_relative_to(ROOT) or not dest.is_file():
                    errors.append(f"Broken/escaping link: {path.relative_to(ROOT)} -> {target}")
    for filename in ["evidence-register.csv", "example-evidence.csv"]:
        with (SKILL / "references" / filename).open(encoding="utf-8", newline="") as stream:
            rows = list(csv.reader(stream))
        if not rows or rows[0] != FIELDS:
            errors.append(f"CSV header mismatch: {filename}")
        if any(len(row) != len(FIELDS) for row in rows[1:]):
            errors.append(f"CSV row width mismatch: {filename}")
        if filename == "example-evidence.csv":
            ids = [row[0] for row in rows[1:] if row]
            if len(ids) < 3 or len(ids) != len(set(ids)):
                errors.append("Example needs three distinct sample IDs")
            report = (SKILL / "references/worked-example.md").read_text(encoding="utf-8")
            for sample_id in ids:
                if sample_id not in report:
                    errors.append(f"Example report lacks sample: {sample_id}")
    # Inspect release candidates rather than ignored local data; report only paths.
    listing = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                             cwd=ROOT, capture_output=True, check=True)
    secret_pattern = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
    candidates = [x.decode("utf-8") for x in listing.stdout.split(b"\0") if x]
    for name in candidates:
        path = ROOT / name
        if not path.is_file():
            continue
        if name.startswith((".local/", ".env")) or path.suffix in {".db", ".sqlite", ".pem", ".key", ".dpapi"}:
            errors.append(f"Private/runtime file in release candidates: {name}")
        if path.stat().st_size > 1024 * 1024:
            errors.append(f"Unexpected file larger than 1 MiB: {name}")
        try:
            value = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            errors.append(f"Non-text/unreadable repository file: {name}")
            continue
        if secret_pattern.search(value):
            errors.append(f"Possible secret in release candidate: {name}")
    if not (ROOT / "LICENSE").is_file():
        errors.append("LICENSE missing")
    return errors, paths


def package(paths):
    directory = ROOT / ".local" / "releases"
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / f"{NAME}-{VERSION}.zip"
    entries = {f"{NAME}/{p.relative_to(SKILL).as_posix()}": p.read_bytes() for p in paths}
    entries[f"{NAME}/LICENSE"] = (ROOT / "LICENSE").read_bytes()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None or set(bundle.namelist()) != set(entries):
            raise ValueError("Archive verification failed")
        if any(bundle.read(name) != data for name, data in entries.items()):
            raise ValueError("Archive contents differ from source")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = directory / "SHA256SUMS.txt"
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return {"archive": archive.relative_to(ROOT).as_posix(), "bytes": archive.stat().st_size,
            "entries": len(entries), "sha256": digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", action="store_true")
    args = parser.parse_args()
    errors, paths = check()
    result = {"ok": not errors, "version": VERSION, "skill_files": len(paths), "errors": errors}
    if not errors and args.package:
        result["package"] = package(paths)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
