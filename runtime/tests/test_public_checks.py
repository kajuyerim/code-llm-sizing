import importlib.util
import unittest
from pathlib import Path

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
