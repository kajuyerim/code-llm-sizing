import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'check_public.py'
spec=importlib.util.spec_from_file_location('public_scan',path)
scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)


class PublicChecks(unittest.TestCase):
    def test_secret_is_detected_without_echoing_value(self):
        value='sk-'+'x'*32
        findings=scanner.scan_text('token '+value,'example.txt')
        self.assertTrue(findings)
        self.assertFalse(any(value in item for item in findings))

    def test_decoded_html_data_is_scanned(self):
        encoded='"'+'\\u0073\\u006b-'+'x'*32+'"'
        text='<script type="application/json">'+encoded+'</script>'
        findings=scanner.scan_text(text,'example.html')
        self.assertTrue(any('decoded-' in item for item in findings))

    def test_auth_names_and_placeholders_are_not_credentials(self):
        self.assertEqual(scanner.scan_text('Use ANTHROPIC_API_KEY from your environment.', 'guide.md'),[])
        self.assertEqual(scanner.scan_text('password="your-placeholder-value"','example.txt'),[])

    def test_auth_files_are_never_publishable(self):
        for name in ('.env','sample/.env.local','auth.json','private.pem','.claude/settings.json','.netrc','.git-credentials'):
            self.assertTrue(scanner.forbidden_file(name))

    def test_unquoted_assignments_and_credential_queries(self):
        value='z'*24
        for text in ('export API_KEY='+value, 'https://example.invalid/?access_token='+value):
            findings=scanner.scan_text(text,'example.txt')
            self.assertTrue(findings)
            self.assertFalse(any(value in item for item in findings))

    def test_pdf_review_is_bound_to_path_and_content_in_checkout_and_history(self):
        reviewed = b'%PDF-1.7\n%\xff\n%%EOF\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args])

            git('init', '-q')
            report = root / 'report.pdf'
            report.write_bytes(reviewed)
            record = root / 'reviews.json'
            record.write_text(json.dumps([{'path': report.name, 'sha256': hashlib.sha256(reviewed).hexdigest()}]))
            with patch.object(scanner, 'PDF_REVIEWS', record):
                self.assertEqual(scanner.scan_repository(root)[1], [])
                report.write_bytes(reviewed + b' ')
                (root / 'copy.pdf').write_bytes(reviewed)
                (root / 'new.pdf').write_bytes(b'%PDF-1.4\n%%EOF\n')
                expected = [f'{name}: binary-file-requires-manual-review'
                            for name in ('copy.pdf', 'new.pdf', 'report.pdf')]
                self.assertEqual(scanner.scan_repository(root)[1], expected)
                git('add', '.')
                git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                    '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'PDF fixtures')
                git('rm', '-q', 'copy.pdf', 'new.pdf')
                report.write_bytes(reviewed)
                git('add', 'report.pdf')
                git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                    '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Restore reviewed PDF')
                self.assertEqual(scanner.scan_repository(root)[1], [])
                findings = scanner.scan_repository(root, history=True)[1]
                self.assertTrue(all(item.startswith('history:') for item in findings))
                self.assertCountEqual([item.split(':', 2)[2] for item in findings], expected)
