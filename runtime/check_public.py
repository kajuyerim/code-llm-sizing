"""Scan public files and optional Git history. Never print matched values."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

PATTERNS = {
    'provider-token': r'\b(?:sk-(?:ant-[A-Za-z0-9_-]{20,}|proj-[A-Za-z0-9_-]{20,}|[A-Za-z0-9_-]{24,})|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}|AKIA[0-9A-Z]{16})\b',
    'private-key': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----',
    'jwt': r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b',
    'authorization': r'(?i)\b(?:authorization[\s"\x27:=]+(?:bearer|basic)\s+)[A-Za-z0-9_./+=-]{16,}',
    'credential-url': r'(?i)\b(?:https?|postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s:/]+:[^\s/@]{6,}@',
    'cookie': r'(?i)\b(?:set-cookie|cookie)[\s"\x27:=]+[^\s"\x27;=]{2,}=[A-Za-z0-9_./+=-]{16,}',
    'secret-assignment': r'(?i)\b(?:[A-Z_]*(?:API_KEY|AUTH_TOKEN|PASSWORD|CLIENT_SECRET|ACCESS_TOKEN|REFRESH_TOKEN)|apiKey|clientSecret|password|accessToken|refreshToken)["\x27\s]*[:=]\s*["\x27]([A-Za-z0-9_./+=-]{12,})["\x27]',
    'unquoted-secret': r'(?im)^\s*(?:export\s+)?(?:[A-Z_]*(?:API_KEY|AUTH_TOKEN|PASSWORD|CLIENT_SECRET|ACCESS_TOKEN|REFRESH_TOKEN)|token|secret)\s*=\s*([A-Za-z0-9_./+=-]{8,})\s*$',
    'credential-query': r'(?i)[?&](?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)=([A-Za-z0-9_%./+=-]{8,})',
}
PATTERNS = {k: re.compile(v) for k, v in PATTERNS.items()}
SENSITIVE_NAMES = {'auth.json', 'credentials.json', '.credentials.json', '.env', '.DS_Store',
                   '.netrc', '.pypirc', '.git-credentials', 'cookies.txt'}


def scan_text(text: str, label: str) -> list[str]:
    """Scan raw text plus recursively decoded JSON strings, including inline HTML data."""
    findings = set()

    def scan(value: str, where: str):
        for category, pattern in PATTERNS.items():
            for match in pattern.finditer(value):
                if category in {'secret-assignment', 'unquoted-secret', 'credential-query'}:
                    literal = match.group(1).lower()
                    if any(x in literal for x in ('example', 'placeholder', 'your_', 'your-', 'not-a-real')):
                        continue
                line = value.count('\n', 0, match.start()) + 1
                findings.add(f'{where}:{line}: {category}')

    def walk(value, where):
        if isinstance(value, str):
            scan(value, where)
        elif isinstance(value, dict):
            for i, value in enumerate(value.values()):
                walk(value, f'{where}/field-{i}')
        elif isinstance(value, list):
            for i, value in enumerate(value):
                walk(value, f'{where}/{i}')

    scan(text, label)
    candidates = [text, *re.findall(r'<script[^>]*type=["\x27]application/json["\x27][^>]*>(.*?)</script>', text, re.S)]
    for i, candidate in enumerate(candidates):
        try:
            walk(json.loads(html.unescape(candidate)), f'{label}:decoded-{i}')
        except (json.JSONDecodeError, TypeError):
            pass
    return sorted(findings)


def forbidden_file(name: str) -> bool:
    p = Path(name)
    return (p.name in SENSITIVE_NAMES or p.name.startswith('.env.') and p.name != '.env.example'
            or p.suffix in {'.pem', '.key'} or any(x in {'.claude', '.codex', '.aws'} for x in p.parts))


PDF_REVIEWS = Path(__file__).with_name('reviewed-pdfs.json')


def scan_file(raw: bytes, name: str, label: str, reviews: set[tuple[str, str]]) -> list[str]:
    is_pdf = Path(name).suffix.lower() == '.pdf' or raw.startswith(b'%PDF-')
    try:
        findings = scan_text(raw.decode('utf-8'), label)
        if not is_pdf:
            return findings
    except UnicodeDecodeError:
        findings = []
    if not is_pdf or (name, hashlib.sha256(raw).hexdigest()) not in reviews:
        findings.append(f'{label}: binary-file-requires-manual-review')
    return findings


def scan_repository(root: Path, history: bool = False) -> tuple[int, list[str]]:
    reviews = {(item['path'], item['sha256']) for item in json.loads(PDF_REVIEWS.read_text(encoding='utf-8'))}
    findings, count = [], 0
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args])
    paths = set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0')) - {''}
    for name in sorted(paths):
        path = root / name
        if not path.exists():
            continue  # deleted paths in a pending rename
        count += 1
        if forbidden_file(name):
            findings.append(f'{name}: forbidden-public-file')
        if path.is_symlink():
            findings.append(f'{name}: public-symlink-requires-review')
            continue
        findings += scan_file(path.read_bytes(), name, name, reviews)
    if history:
        trees = set()
        for row in git('log', '--all', '--format=%H %T').decode().splitlines():
            oid, tree = row.split()
            trees.add(tree)
            count += 1
            findings += scan_text(git('show', '-s', '--format=%B', oid).decode('utf-8'),
                                  f'commit:{oid[:12]}')

        # rev-list --objects lists only one name per blob. A copied PDF needs its own path review.
        seen = set()
        for tree in sorted(trees):
            for entry in git('ls-tree', '-r', '-z', tree).split(b'\0'):
                if not entry:
                    continue
                metadata, path_bytes = entry.split(b'\t', 1)
                _, kind, oid = metadata.decode().split()
                name = path_bytes.decode()
                if kind != 'blob' or (oid, name) in seen:
                    continue
                seen.add((oid, name))
                count += 1
                label = f'history:{oid[:12]}:{name}'
                if forbidden_file(name):
                    findings.append(f'{label}: forbidden-public-file')
                findings += scan_file(git('cat-file', 'blob', oid), name, label, reviews)
    return count, sorted(set(findings))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    args = parser.parse_args()
    count, findings = scan_repository(Path(__file__).resolve().parents[1], args.history)
    for finding in findings:
        print(finding)
    print(f'Inspected {count} files/blobs; {len(findings)} findings. Pattern-based scan, not a guarantee.')
    raise SystemExit(bool(findings))
