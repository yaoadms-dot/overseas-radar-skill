"""Read-only SHA-256 duplicate audit; hardlinks count as one storage object."""
import argparse
import hashlib
import json
import os
from pathlib import Path

DEFAULT_SKIP = {'.git', 'node_modules', '__pycache__', 'uv-cache', '.venv', 'site-packages'}
ASSET_SUFFIXES = {'.otf', '.ttf', '.woff', '.woff2', '.bin', '.safetensors', '.onnx', '.pt', '.pth', '.dll', '.exe', '.zip', '.7z', '.mp4', '.mov', '.wav'}

def audit(roots, min_bytes=1048576, assets_only=False):
    sizes, errors, skipped, seen = {}, [], [], set()
    for root in roots:
        root = Path(root).absolute()
        if not root.is_dir() or root.is_symlink() or getattr(root.stat(), 'st_file_attributes', 0) & 0x400:
            errors.append({'path': str(root), 'error': 'invalid or reparse root'})
            continue
        def onerror(e):
            errors.append({'path': str(e.filename), 'error': str(e)})
        for folder, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            keep = []
            for name in dirs:
                p = Path(folder) / name
                try:
                    if name in DEFAULT_SKIP or p.is_symlink() or getattr(p.lstat(), 'st_file_attributes', 0) & 0x400:
                        skipped.append(str(p))
                    else:
                        keep.append(name)
                except OSError as e:
                    errors.append({'path': str(p), 'error': str(e)})
            dirs[:] = keep
            for name in files:
                p = Path(folder) / name
                if str(p) in seen or (assets_only and p.suffix.lower() not in ASSET_SUFFIXES):
                    continue
                seen.add(str(p))
                try:
                    s = p.lstat()
                    if p.is_symlink() or getattr(s, 'st_file_attributes', 0) & 0x400:
                        skipped.append(str(p))
                        continue
                    if s.st_size >= min_bytes:
                        sizes.setdefault(s.st_size, []).append((p, s))
                except OSError as e:
                    errors.append({'path': str(p), 'error': str(e)})
    cache, groups = {}, []
    for size, entries in sizes.items():
        if len(entries) < 2:
            continue
        hashes = {}
        for p, s in entries:
            identity = (s.st_dev, s.st_ino) if s.st_ino else str(p)
            try:
                if identity not in cache:
                    h = hashlib.sha256()
                    with p.open('rb') as f:
                        for block in iter(lambda: f.read(8388608), b''):
                            h.update(block)
                    cache[identity] = h.hexdigest()
                current = p.stat()
                if (current.st_ino, current.st_size, current.st_mtime_ns) != (s.st_ino, s.st_size, s.st_mtime_ns):
                    raise OSError('file changed during audit')
                hashes.setdefault(cache[identity], []).append((str(p), identity))
            except OSError as e:
                errors.append({'path': str(p), 'error': str(e)})
        for sha, matching in hashes.items():
            if len(matching) > 1:
                objects = len({identity for _, identity in matching})
                groups.append({'sha256': sha, 'size': size, 'paths': [p for p, _ in matching], 'path_count': len(matching), 'storage_objects': objects, 'candidate_duplicate_bytes': (objects - 1) * size})
    groups.sort(key=lambda g: g['candidate_duplicate_bytes'], reverse=True)
    return {'schema_version': 1, 'roots': [str(Path(r).absolute()) for r in roots], 'min_bytes': min_bytes, 'assets_only': assets_only, 'excluded_directory_names': sorted(DEFAULT_SKIP), 'files_considered': len(seen), 'candidate_duplicate_bytes': sum(g['candidate_duplicate_bytes'] for g in groups), 'groups': groups, 'errors': errors, 'skipped_paths': skipped, 'limitations': 'Read-only estimate; external hardlinks, compression, legitimate release copies and excluded paths require review. No deletion or automatic consolidation.'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', action='append', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--min-mib', type=float, default=1)
    parser.add_argument('--assets-only', action='store_true')
    parser.add_argument('--fail-mib', type=float, default=256)
    args = parser.parse_args()
    if args.min_mib < 0 or args.fail_mib < 0:
        parser.error('thresholds must be nonnegative')
    result = audit(args.root, int(args.min_mib * 1048576), args.assets_only)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result['exit_code'] = 2 if result['errors'] else 1 if result['candidate_duplicate_bytes'] >= args.fail_mib * 1048576 and result['candidate_duplicate_bytes'] > 0 else 0
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('files_considered', 'candidate_duplicate_bytes', 'exit_code')}, ensure_ascii=False))
    return result['exit_code']

if __name__ == '__main__':
    raise SystemExit(main())
