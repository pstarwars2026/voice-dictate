import unittest

from tools.check_public_boundary import violations


class PublicBoundaryTests(unittest.TestCase):
    def test_public_source_and_documentation_allowed(self):
        for path in ["dictation_core.py", "models/catalog.json", "PRIVACY.md", "docs/RELEASE_CHECKS.md"]:
            with self.subTest(path=path):
                self.assertEqual(violations(path, b"public content"), [])

    def test_private_paths_rejected(self):
        for path in ["commercial/Sources/App.swift", ".env.local", "auth.p8",
                     "App.xcodeproj/project.pbxproj", "App.app/Contents/Info.plist",
                     "docs/release-state.json", "docs/assets/sandbox/test.png",
                     "docs/APPLE_SANDBOX_CHECKS.md", "audio.wav"]:
            with self.subTest(path=path):
                self.assertIn("private-only file", violations(path, b""))

    def test_tokens_rejected_even_under_innocent_filename(self):
        for prefix in [b"gh" + b"p_", b"github" + b"_pat_", b"sk" + b"-proj-", b"hf" + b"_"]:
            with self.subTest(prefix=prefix):
                self.assertTrue(violations("notes.txt", prefix + b"x" * 40))

    def test_private_key_rejected(self):
        header = b"-----BEGIN " + b"PRIVATE KEY-----"
        self.assertEqual(violations("notes.txt", header), ["private key"])

    def test_public_identifiers_not_treated_as_secrets(self):
        self.assertEqual(violations("README.md", b"com.example.product.pro $2.99"), [])


if __name__ == "__main__":
    unittest.main()
