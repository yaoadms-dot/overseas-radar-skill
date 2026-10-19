"""Portable standard-library engine; PowerShell entrypoints are the public interface."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent.parent
STAGES = ['明确目标', '探索方案', '建立工程', '数据与接口', '核心功能', '命令验证', '界面', '验收']
TOKEN = re.compile(r'\{\{([A-Z][A-Z0-9_]*)\}\}')

class Failure(Exception):
    def __init__(self, code, message, exit_code=1):
        super().__init__(message)
        self.code, self.exit_code = code, exit_code

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as e:
        raise Failure('INVALID_JSON', f'{Path(path).name}: {e}') from e

def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def run(argv, cwd=None, timeout=60):
    try:
        p = subprocess.run([str(x) for x in argv], cwd=cwd, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Failure('COMMAND_UNAVAILABLE', str(e), 2) from e

def execute(argv, cwd=None):
    code, out, err = run(argv, cwd)
    if code:
        raise Failure('COMMAND_FAILED', err.decode('utf-8', 'replace')[-3000:] or f'exit {code}')
    return out

def reparse(path):
    if path.is_symlink():
        return True
    return bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)

def safe_relative(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise Failure('UNSAFE_PATH', str(name))
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('..', '.', '') for x in name.split('/')):
        raise Failure('UNSAFE_PATH', name)
    return p

def inside(root, relative):
    safe_relative(relative)
    root = Path(root).resolve()
    p = root.joinpath(*relative.split('/'))
    for part in [p, *p.parents]:
        if part == root:
            break
        if part.exists() and reparse(part):
            raise Failure('REPARSE_PATH', relative)
    if not p.resolve().is_relative_to(root):
        raise Failure('PATH_ESCAPE', relative)
    return p

def version(text):
    m = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', text)
    if not m:
        raise Failure('VERSION_UNREADABLE', text, 2)
    return tuple(int(v or 0) for v in m.groups())

def runtime_check(manifest):
    required = manifest['compatibility']
    if sys.platform not in required['platforms']:
        raise Failure('UNSUPPORTED_PLATFORM', sys.platform, 2)
    results = []
    checks = [('python', '.'.join(map(str, sys.version_info[:3])), required['python_min'])]
    tools = [('git', ['git', '--version'], 'git_min')]
    if sys.platform == 'win32':
        tools.append(('powershell', ['pwsh', '-NoProfile', '-Command', '$PSVersionTable.PSVersion.ToString()'], 'powershell_min'))
    for tool, argv, minimum_key in tools:
        output = execute(argv).decode('utf-8', 'replace').strip()
        checks.append((tool, output, required[minimum_key]))
    for tool, actual, minimum in checks:
        if version(actual) < version(minimum):
            raise Failure('INCOMPATIBLE_RUNTIME', f'{tool}: {actual}; minimum {minimum}', 2)
        results.append({'id': 'runtime.' + tool, 'status': 'pass', 'actual': actual, 'minimum': minimum})
    return results

def load_manifest(root, check_runtime=True):
    root = Path(root).resolve()
    path = root / 'template-manifest.json'
    m = read_json(path)
    if m.get('schema_version') != 1 or m.get('template_id') != 'software-project-baseline':
        raise Failure('MANIFEST_SCHEMA', 'Unsupported manifest ID or schema')
    if not re.fullmatch(r'v\d+\.\d+\.\d+', m.get('version', '')):
        raise Failure('MANIFEST_VERSION', 'Invalid version')
    paths, outputs = set(), set()
    compatibility = m.get('compatibility', {})
    platforms = compatibility.get('platforms')
    if not isinstance(platforms, list) or set(platforms) != {'win32', 'darwin', 'linux'}:
        raise Failure('MANIFEST_PLATFORMS', 'Expected win32, darwin and linux')
    if not isinstance(compatibility.get('entrypoints'), dict):
        raise Failure('MANIFEST_ENTRYPOINTS', 'Missing platform entrypoints')
    variables = m.get('variables', {})
    for key, spec in variables.items():
        if key not in ('PROJECT_NAME', 'GENERATED_AT', 'BASELINE_VERSION') or spec.get('type') != 'string':
            raise Failure('UNKNOWN_VARIABLE', key)
    for entry in m.get('files', []):
        name = entry['path']
        p = inside(root, name)
        if name.casefold() in paths or name == 'template-manifest.json':
            raise Failure('DUPLICATE_SOURCE', name)
        paths.add(name.casefold())
        if not p.is_file() or sha(p.read_bytes()) != entry['sha256']:
            raise Failure('FILE_HASH_MISMATCH', name)
        if entry.get('role') not in ('template', 'rule', 'tool'):
            raise Failure('INVALID_ROLE', name)
        if entry['role'] == 'template':
            out = entry.get('output', '')
            safe_relative(out)
            if out.casefold() in outputs or out.split('/')[0].casefold() in ('.git', '.project-baseline', '.local'):
                raise Failure('DUPLICATE_OR_RESERVED_OUTPUT', out)
            outputs.add(out.casefold())
            if entry.get('format') not in ('text', 'json'):
                raise Failure('UNKNOWN_FORMAT', name)
            content = p.read_text(encoding='utf-8')
            for variable in TOKEN.findall(content):
                if variable not in variables or name not in variables[variable]['files']:
                    raise Failure('UNKNOWN_VARIABLE', f'{name}: {variable}')
            if '{{' in TOKEN.sub('', content) or '}}' in TOKEN.sub('', content):
                raise Failure('INVALID_PLACEHOLDER', name)
    for folder in ('templates', 'tools'):
        actual = {p.relative_to(root).as_posix().casefold() for p in (root / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        declared = {p for p in paths if p.startswith(folder + '/')}
        if actual != declared:
            raise Failure('UNDECLARED_PAYLOAD', folder)
    for name in ('rules.md',):
        if name not in paths:
            raise Failure('MISSING_RULES', name)
    for variable, spec in variables.items():
        if not spec['files'] or any(p.casefold() not in paths for p in spec['files']):
            raise Failure('VARIABLE_SCOPE', variable)
    if not outputs or not {'readme.md', 'agents.md', 'project.json', '.gitignore', '.gitattributes'}.issubset(outputs):
        raise Failure('MISSING_REQUIRED_OUTPUT', 'Required project entrypoints are not declared')
    for platform in platforms:
        entrypoints = compatibility['entrypoints'].get(platform)
        if not isinstance(entrypoints, dict) or set(entrypoints) != {'init', 'check'}:
            raise Failure('MANIFEST_ENTRYPOINTS', platform)
        for purpose, relative in entrypoints.items():
            if not isinstance(relative, str) or relative not in paths:
                raise Failure('MANIFEST_ENTRYPOINT', f'{platform}:{purpose}')
            entry = next(item for item in m['files'] if item['path'] == relative)
            if entry['role'] != 'tool':
                raise Failure('MANIFEST_ENTRYPOINT', f'{platform}:{purpose}')
    if check_runtime:
        runtime_check(m)
    return m, sha(path.read_bytes())

def render(value, variables):
    if isinstance(value, str):
        return TOKEN.sub(lambda match: variables[match.group(1)], value)
    if isinstance(value, list):
        return [render(v, variables) for v in value]
    if isinstance(value, dict):
        return {k: render(v, variables) for k, v in value.items()}
    return value

def tree_hash(manifest):
    lines = [f"{x['path']}\0{x['sha256']}" for x in sorted(manifest['files'], key=lambda x: x['path'])]
    return sha('\n'.join(lines).encode())

def check_project(project, stage='基准完整性', execute_checks=True):
    project = Path(project).resolve()
    snap = project / '.project-baseline'
    m, digest = load_manifest(snap)
    adoption = read_json(snap / 'adoption.json')
    if adoption.get('manifest_sha256') != digest or adoption.get('template_sha256') != tree_hash(m) or adoption.get('version') != m['version']:
        raise Failure('ADOPTION_MISMATCH', 'Snapshot and adoption differ')
    if reparse(snap) or not (project / '.git').is_dir() or reparse(project / '.git'):
        raise Failure('INVALID_PROJECT_ROOT', 'Snapshot and Git must be local directories')
    git_top = Path(execute(['git', 'rev-parse', '--show-toplevel'], project).decode('utf-8').strip()).resolve()
    if git_top != project:
        raise Failure('INVALID_PROJECT_ROOT', 'Git root differs from project root')
    initial = execute(['git', 'rev-parse', 'refs/baselines/initial'], project).decode().strip()
    parents = execute(['git', 'rev-list', '--parents', '-n', '1', initial], project).decode().split()
    if len(parents) != 1:
        raise Failure('NOT_INITIAL_COMMIT', initial)
    execute(['git', 'merge-base', '--is-ancestor', initial, 'HEAD'], project)
    expected_snapshot = {x['path'] for x in m['files']} | {'template-manifest.json', 'adoption.json'}
    actual_snapshot = {p.relative_to(snap).as_posix() for p in snap.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    if expected_snapshot != actual_snapshot:
        raise Failure('SNAPSHOT_INVENTORY', 'Incomplete or unexpected snapshot files')
    for name in expected_snapshot:
        committed = execute(['git', 'show', f'{initial}:.project-baseline/{name}'], project)
        if committed != inside(snap, name).read_bytes():
            raise Failure('SNAPSHOT_CHANGED', name)
    for entry in m['files']:
        if entry['role'] != 'template':
            continue
        path = inside(project, entry['output'])
        if not path.is_file():
            raise Failure('MISSING_GENERATED_FILE', entry['output'])
        text = path.read_text(encoding='utf-8-sig')
        if '{{' in text or '}}' in text:
            raise Failure('REMAINING_PLACEHOLDER', entry['output'])
    facts = [{'id': 'snapshot.integrity', 'status': 'pass', 'manifest_sha256': digest, 'template_sha256': tree_hash(m), 'initial_commit': initial}]
    if stage == '基准完整性':
        return facts, m, digest
    config = read_json(project / 'project.json')
    if config.get('schema_version') != 1 or config.get('baseline_version') != m['version']:
        raise Failure('PROJECT_CONFIG_VERSION', 'Project configuration differs from adopted version')
    if stage not in STAGES:
        raise Failure('INVALID_STAGE', stage, 2)
    stage_data = config.get('stages', {}).get(stage, {})
    if stage_data.get('status') == 'skipped':
        if not stage_data.get('reason', '').strip():
            raise Failure('SKIP_WITHOUT_REASON', stage)
        if stage in ('明确目标', '建立工程', '验收'):
            raise Failure('REQUIRED_STAGE', stage)
        facts.append({'id': 'stage', 'status': 'skipped', 'reason': stage_data['reason']})
        return facts, m, digest
    if stage_data.get('status') != 'complete':
        raise Failure('STAGE_INCOMPLETE', stage)
    required = m['stages'][stage]['required_fields']
    for field in required:
        value = config.get('facts', {}).get(field, '')
        if not isinstance(value, str) or not value.strip() or value.strip() in ('待补充', '待确认', 'TODO'):
            raise Failure('MISSING_STAGE_FACT', field)
    evidence = stage_data.get('evidence', [])
    if not evidence:
        raise Failure('MISSING_EVIDENCE', stage)
    for file in evidence:
        if not inside(project, file).is_file():
            raise Failure('EVIDENCE_NOT_FOUND', file)
    checks = [c for c in config.get('checks', []) if c.get('enabled') and stage in c.get('stages', [])]
    if m['stages'][stage]['requires_commands'] and not checks:
        raise Failure('NO_EXECUTABLE_CHECK', stage)
    for check in checks:
        program, args = check.get('program'), check.get('args')
        if not isinstance(program, str) or not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise Failure('INVALID_COMMAND_CONFIG', check.get('id', ''), 2)
        working = project if check.get('cwd', '.') == '.' else inside(project, check['cwd'])
        if not working.is_dir():
            raise Failure('INVALID_WORKING_DIRECTORY', check['id'], 2)
        timeout = check.get('timeout_seconds', 60)
        if not isinstance(timeout, int) or timeout < 1 or timeout > 300:
            raise Failure('INVALID_TIMEOUT', check['id'], 2)
        if execute_checks:
            code, out, err = run([program, *args], working, timeout)
            facts.append({'id': check['id'], 'status': 'pass' if code == 0 else 'fail', 'command': [program, *args], 'exit_code': code, 'stdout': out.decode('utf-8', 'replace')[-4000:], 'stderr': err.decode('utf-8', 'replace')[-4000:]})
    facts.append({'id': 'stage.' + stage, 'status': 'pass', 'evidence': evidence})
    return facts, m, digest

def clean_owned(staging, parent, owner):
    staging, parent = Path(staging), Path(parent).resolve()
    if staging.parent.resolve() != parent or not staging.name.startswith('.baseline-staging-') or reparse(staging):
        raise Failure('CLEANUP_PATH_REJECTED', str(staging), 2)
    if read_json(staging / '.baseline-owner.json').get('owner') != owner:
        raise Failure('CLEANUP_OWNER_REJECTED', str(staging), 2)
    for p in staging.rglob('*'):
        if reparse(p):
            raise Failure('CLEANUP_REPARSE_REJECTED', str(p), 2)
    shutil.rmtree(staging, onerror=lambda fn, p, _: (os.chmod(p, 0o700), fn(p)))

def initialize(root, name, target):
    root = Path(root).resolve()
    target = Path(os.path.abspath(target))
    if not name.strip() or any(ord(c) < 32 for c in name) or '{{' in name or '}}' in name:
        raise Failure('INVALID_NAME', 'Invalid project name', 2)
    if target.exists() or target.is_symlink():
        raise Failure('TARGET_EXISTS', str(target))
    if not target.parent.is_dir():
        raise Failure('PARENT_MISSING', str(target.parent), 2)
    if any(reparse(p) for p in (target.parent, *target.parent.parents)):
        raise Failure('REPARSE_PARENT', str(target.parent), 2)
    if target.is_relative_to(root) or root.is_relative_to(target):
        raise Failure('TARGET_OVERLAPS_BASELINE', str(target))
    m, digest = load_manifest(root)
    execute(['git', 'var', 'GIT_AUTHOR_IDENT'], target.parent)
    execute(['git', 'var', 'GIT_COMMITTER_IDENT'], target.parent)
    owner = uuid.uuid4().hex
    staging = target.parent / ('.baseline-staging-' + owner)
    staging.mkdir()
    write_json(staging / '.baseline-owner.json', {'owner': owner})
    try:
        variables = {'PROJECT_NAME': name, 'GENERATED_AT': now(), 'BASELINE_VERSION': m['version']}
        snap = staging / '.project-baseline'
        snap.mkdir()
        shutil.copyfile(root / 'template-manifest.json', snap / 'template-manifest.json')
        for entry in m['files']:
            src = inside(root, entry['path'])
            dest = inside(snap, entry['path'])
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            if entry['role'] == 'template':
                out = inside(staging, entry['output'])
                out.parent.mkdir(parents=True, exist_ok=True)
                if entry['format'] == 'json':
                    write_json(out, render(read_json(src), variables))
                else:
                    out.write_text(render(src.read_text(encoding='utf-8'), variables), encoding='utf-8')
        adoption = {'schema_version': 1, 'template_id': m['template_id'], 'version': m['version'], 'manifest_sha256': digest, 'template_sha256': tree_hash(m), 'generated_at': variables['GENERATED_AT'], 'upgrade_policy': 'explicit-only'}
        write_json(snap / 'adoption.json', adoption)
        execute(['git', 'init', '--initial-branch=main'], staging)
        execute(['git', 'config', 'core.autocrlf', 'false'], staging)
        execute(['git', 'add', '--all'], staging)
        execute(['git', 'commit', '-m', 'chore: initialize project from baseline ' + m['version']], staging)
        commit = execute(['git', 'rev-parse', 'HEAD'], staging).decode().strip()
        execute(['git', 'update-ref', 'refs/baselines/initial', commit], staging)
        checks, _, _ = check_project(staging)
        receipt = {**adoption, 'initial_commit': commit, 'target': str(target), 'checks': checks}
        (staging / '.local').mkdir(exist_ok=True)
        write_json(staging / '.local' / 'initialization-receipt.json', receipt)
        if target.exists() or target.is_symlink():
            raise Failure('TARGET_EXISTS', str(target))
        # Windows os.rename refuses an existing destination; same-parent rename is the commit point.
        # Keep the ignored ownership marker so pre-commit-point cleanup can always verify ownership.
        os.rename(staging, target)
        return receipt
    except BaseException:
        if staging.exists():
            clean_owned(staging, target.parent, owner)
        raise

def check_mother(root):
    root = Path(root).resolve()
    m, digest = load_manifest(root)
    facts = runtime_check(m)
    allowed = {'.git', '.gitignore', '.gitattributes', 'AGENTS.md', 'README.md', 'rules.md', 'CHANGELOG.md', 'template-manifest.json', 'tools', 'templates', 'tests', 'evidence'}
    unknown = sorted(p.name for p in root.iterdir() if p.name not in allowed)
    if unknown:
        raise Failure('UNEXPECTED_BASELINE_CONTENT', ', '.join(unknown))
    for entry in m['files']:
        if entry['role'] == 'template' and Path(entry['path']).suffix in ('.md', '.json'):
            content = inside(root, entry['path']).read_text(encoding='utf-8')
            if re.search(r'[A-Za-z]:[\\/]|https?://|wxid_|(?i:token\s*[:=]\s*[a-z0-9]{16,})', content):
                raise Failure('TEMPLATE_BUSINESS_OR_LOCAL_DATA', entry['path'])
    current_entrypoints = m['compatibility']['entrypoints'][sys.platform]
    for purpose, relative in current_entrypoints.items():
        name = Path(relative).name
        if sys.platform == 'win32':
            argv = ['pwsh', '-NoProfile', '-File', str(inside(root, relative)), '-Probe']
        else:
            argv = ['sh', str(inside(root, relative)), '--probe']
        code, out, err = run(argv)
        if code or read_probe(out) != 'baseline-tool-ready':
            raise Failure('TOOL_NOT_EXECUTABLE', name + ': ' + err.decode('utf-8', 'replace'), 2)
        facts.append({'id': 'tool.' + purpose, 'status': 'pass', 'command': argv, 'exit_code': code})
    facts.append({'id': 'mother.integrity', 'status': 'pass', 'manifest_sha256': digest, 'file_count': len(m['files'])})
    facts.append({'id': 'mother.semantic_review', 'status': 'requires-review', 'reason': 'Automated scans do not establish business neutrality; release requires recorded human/agent review.'})
    return facts, m, digest

def read_probe(out):
    try:
        return json.loads(out.decode('utf-8-sig'))['status']
    except (ValueError, KeyError):
        return ''

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='operation', required=True)
    sub.add_parser('probe')
    init = sub.add_parser('init')
    init.add_argument('--name', required=True)
    init.add_argument('--target', required=True)
    init.add_argument('--root', default=str(ROOT))
    check = sub.add_parser('check')
    check.add_argument('--mode', choices=['mother', 'project'], default='project')
    check.add_argument('--root', default=str(ROOT))
    check.add_argument('--project')
    check.add_argument('--stage', default='基准完整性')
    args = parser.parse_args()
    output = {'schema_version': 1, 'started_at': now(), 'checks': []}
    try:
        if args.operation == 'probe':
            print(json.dumps({'status': 'baseline-tool-ready'}))
            return 0
        if args.operation == 'init':
            output['data'] = initialize(args.root, args.name, args.target)
            output['checks'] = output['data']['checks']
        else:
            if args.mode == 'mother':
                facts, m, digest = check_mother(args.root)
            else:
                if not args.project:
                    raise Failure('PROJECT_PATH_REQUIRED', '--project', 2)
                facts, m, digest = check_project(args.project, args.stage)
            output.update(checks=facts, baseline_version=m['version'], manifest_sha256=digest)
        code = 1 if any(x['status'] == 'fail' for x in output['checks']) else 0
        output.update(ok=code == 0, exit_code=code)
    except Failure as e:
        code = e.exit_code
        output.update(ok=False, exit_code=code, error={'code': e.code, 'message': str(e)})
    except Exception as e:
        code = 2
        output.update(ok=False, exit_code=code, error={'code': 'RUNTIME_ERROR', 'message': str(e)})
    output['finished_at'] = now()
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return code

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
