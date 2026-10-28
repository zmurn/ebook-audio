"""Tests for the Slovenian pronunciation layer."""

import subprocess
import unittest

from pron_sl import audit, pronounce, suggest


def ipa(word: str) -> str:
    return subprocess.run(
        ["espeak-ng", "-v", "sl", "-q", "--ipa", word],
        capture_output=True, text=True,
    ).stdout.strip()


class TestPronounce(unittest.TestCase):
    def test_names(self):
        self.assertEqual(pronounce("Mozart in Bach")[0], "Mocart in Bah")
        self.assertEqual(pronounce("Laibach")[0], "Lajbah")

    def test_inflected_forms(self):
        self.assertEqual(pronounce("Bacha")[0], "Baha")
        self.assertEqual(pronounce("Mozarta")[0], "Mocarta")
        self.assertEqual(pronounce("Beethovna")[0], "Betovna")

    def test_multiword_and_case(self):
        self.assertEqual(pronounce("New York")[0], "Njujork")
        self.assertEqual(pronounce("MOZART")[0], "MOCART")

    def test_slovenian_text_untouched(self):
        text = "Jesensko jutro se je vleklo čez Ljubljansko barje."
        self.assertEqual(pronounce(text), (text, []))

    def test_resulting_phonemes(self):
        self.assertIn("x", ipa(pronounce("Bach")[0]))
        self.assertIn("ts", ipa(pronounce("Mozart")[0]))
        self.assertTrue(ipa(pronounce("Shakespeare")[0]).startswith("ʃ"))


class TestAudit(unittest.TestCase):
    def test_flags_unknown_name(self):
        found = audit("Leta 1990 je Schwarzenegger igral.")
        self.assertEqual([f[0] for f in found], ["Schwarzenegger"])

    def test_ignores_known_names(self):
        self.assertEqual(audit("Nietzsche in Mozart"), [])

    def test_suggest_is_advisory(self):
        guess = suggest("Schwarzenegger")
        self.assertIsNotNone(guess)
        self.assertTrue(guess[0].startswith("šv"))


if __name__ == "__main__":
    unittest.main()
