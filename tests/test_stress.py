"""Stress placement on Piper phonemes."""

import unittest

from sl_stress import apply, syllable_starts


class TestStress(unittest.TestCase):
    def test_syllable_starts(self):
        phonemes = ["b", "ɛ", "t", "o", "ː", "ʋ", "ə", "n"]
        self.assertEqual(syllable_starts(phonemes), [1, 3, 6])

    def test_move_stress(self):
        # bɛtˈoːʋən -> stress on the first syllable
        out = apply(["b", "ɛ", "t", "ˈ", "o", "ː", "ʋ", "ə", "n"], 1)
        self.assertEqual(out, ["b", "ˈ", "ɛ", "t", "o", "ː", "ʋ", "ə", "n"])

    def test_keeps_single_stress(self):
        self.assertEqual(apply(["s", "ˈ", "a", "m", "ɔ"], 2).count("ˈ"), 1)

    def test_out_of_range_is_ignored(self):
        self.assertEqual(apply(["a", "b"], 9), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
