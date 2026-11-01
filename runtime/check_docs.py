"""Check local Markdown links, frontmatter, and authored prose without model calls."""
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]


def check():
    failures = []
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
    files = sorted({ROOT / n for n in names if n.endswith('.md') and (ROOT / n).is_file()})
    def anchors(text):
        result = set(); used = {}
        for heading in re.findall(r'^#{1,6}\s+(.+)$', text, re.M):
            slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
            n = used.get(slug, 0); used[slug] = n + 1
            result.add(slug + (f'-{n}' if n else ''))
        return result
    for p in files:
        text = p.read_text()
        label = p.relative_to(ROOT)
        if '\u2014' in text:
            failures.append(f'{label}: em dash in authored Markdown')
        if text.startswith('---\n'):
            try:
                meta = yaml.safe_load(text.split('---', 2)[1])
                if not isinstance(meta, dict):
                    failures.append(f'{label}: frontmatter must be a mapping')
            except yaml.YAMLError:
                failures.append(f'{label}: invalid frontmatter')
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            target = target.strip('<>')
            if re.match(r'^[a-z]+://|^mailto:', target):
                continue
            path, _, fragment = unquote(target).partition('#')
            dest = (p.parent / path).resolve() if path else p
            if not dest.exists():
                failures.append(f'{label}: broken link {target}')
            elif fragment and dest.suffix == '.md' and fragment not in anchors(dest.read_text()):
                failures.append(f'{label}: missing anchor {target}')
    return files, failures


if __name__ == '__main__':
    files, failures = check()
    for failure in failures:
        print(failure)
    print(f'Checked {len(files)} Markdown documents; {len(failures)} findings.')
    raise SystemExit(bool(failures))
