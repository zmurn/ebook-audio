"""Regression tests: every ✗ in bakeoff/frontend.md must become ✓ here."""

import unittest

from norm_sl import int_to_words, normalize, ordinal, plural_form


def n(text: str) -> str:
    return normalize(text)[0]


class TestNumerals(unittest.TestCase):
    def test_cardinals(self):
        self.assertEqual(int_to_words(0), "nič")
        self.assertEqual(int_to_words(1), "en")
        self.assertEqual(int_to_words(2, "f"), "dve")
        self.assertEqual(int_to_words(21), "enaindvajset")
        self.assertEqual(int_to_words(100), "sto")
        self.assertEqual(int_to_words(101), "sto en")
        self.assertEqual(int_to_words(1848), "tisoč osemsto oseminštirideset")
        self.assertEqual(int_to_words(36500), "šestintrideset tisoč petsto")
        self.assertEqual(int_to_words(2_000_000), "dva milijona")

    def test_plural_form(self):
        forms = ("ura", "uri", "ure", "ur")
        self.assertEqual(plural_form(1, forms), "ura")
        self.assertEqual(plural_form(2, forms), "uri")
        self.assertEqual(plural_form(3, forms), "ure")
        self.assertEqual(plural_form(5, forms), "ur")
        self.assertEqual(plural_form(11, forms), "ur")
        self.assertEqual(plural_form(21, forms), "ur")
        self.assertEqual(plural_form(101, forms), "ura")

    def test_ordinals(self):
        self.assertEqual(ordinal(1), "prvi")
        self.assertEqual(ordinal(3), "tretji")
        self.assertEqual(ordinal(3, case="loc"), "tretjem")
        self.assertEqual(ordinal(19, case="loc"), "devetnajstem")
        self.assertEqual(ordinal(21), "enaindvajseti")
        self.assertEqual(ordinal(5, "n"), "peto")
        self.assertEqual(ordinal(2, case="gen"), "drugega")


class TestNormalize(unittest.TestCase):
    def test_ordinals_before_nouns(self):
        self.assertEqual(n("V 3. nadstropju"), "V tretjem nadstropju")
        self.assertEqual(n("V 19. stoletju"), "V devetnajstem stoletju")
        self.assertEqual(n("5. poglavje"), "peto poglavje")
        self.assertEqual(n("II. del"), "drugi del")
        self.assertEqual(n("v 2. izdaji"), "v drugi izdaji")

    def test_dates(self):
        self.assertEqual(n("1. 5. 2024"), "prvega maja dva tisoč štiriindvajset")
        self.assertEqual(n("3. marca 1900"), "tretjega marca tisoč devetsto")

    def test_money(self):
        self.assertEqual(n("14,80 evra"), "štirinajst evrov osemdeset centov")
        self.assertEqual(n("1,50 €"), "en evro petdeset centov")
        self.assertEqual(n("5 €"), "pet evrov")

    def test_units(self):
        self.assertEqual(n("2 kg"), "dva kilograma")
        self.assertEqual(n("12 km/h"), "dvanajst kilometrov na uro")
        self.assertEqual(n("21 °C"), "enaindvajset stopinj Celzija")
        self.assertEqual(n("65 %"), "petinšestdeset odstotkov")
        self.assertEqual(n("2 uri"), "dve uri")
        self.assertEqual(n("15 minut"), "petnajst minut")
        self.assertEqual(n("3,5 kg"), "tri kilograme in pol")

    def test_abbreviations(self):
        self.assertEqual(n("npr."), "na primer")
        self.assertEqual(n("itd."), "in tako dalje")
        self.assertEqual(n("dr. Novak"), "doktor Novak")
        self.assertEqual(n("str. 5"), "stran pet")
        self.assertEqual(n("št. 12"), "številka dvanajst")
        self.assertEqual(n("t. i. roman"), "tako imenovani roman")
        self.assertEqual(n("prof."), "profesor")

    def test_thousands_and_plain(self):
        self.assertEqual(n("1.278"), "tisoč dvesto oseminsedemdeset")
        self.assertEqual(n("36.500"), "šestintrideset tisoč petsto")
        self.assertEqual(n("leta 1848"), "leta tisoč osemsto oseminštirideset")
        self.assertEqual(n("8:30"), "osem trideset")

    def test_ambiguous_dot(self):
        self.assertEqual(n("500 g. moke"), "petsto gramov moke")
        self.assertEqual(n("500 g. Potem je tiho."), "petsto gramov. Potem je tiho.")
        self.assertEqual(n("g. Novak"), "gospod Novak")
        self.assertEqual(n("Ga. Kovač"), "Gospa Kovač")
        self.assertEqual(n("sl. 5"), "slika pet")

    def test_unknown_ordinal_is_flagged_not_guessed(self):
        text, warnings = normalize("3. neznanka")
        self.assertIn("3.", text)
        self.assertTrue(any("unknown noun" in w for w in warnings))

    def test_initials_untouched(self):
        self.assertEqual(n("M. Kacjan"), "M. Kacjan")


if __name__ == "__main__":
    unittest.main()


class TestMinimalMode(unittest.TestCase):
    """Minimal mode must leave alone what eSpeak already reads with good stress."""

    def test_keeps_digits(self):
        self.assertEqual(normalize("1848", minimal=True)[0], "1848")
        self.assertEqual(normalize("36.500", minimal=True)[0], "36.500")
        self.assertEqual(normalize("65 %", minimal=True)[0], "65 %")
        self.assertEqual(normalize("15 minut", minimal=True)[0], "15 minut")
        self.assertEqual(normalize("3 ure", minimal=True)[0], "3 ure")

    def test_fixes_only_errors(self):
        self.assertEqual(normalize("2 uri", minimal=True)[0], "dve uri")
        self.assertEqual(normalize("2 knjigi", minimal=True)[0], "dve knjigi")
        self.assertEqual(normalize("št. 12", minimal=True)[0], "številka 12")
        self.assertEqual(normalize("3. nadstropju", minimal=True)[0], "tretjem nadstropju")
        self.assertEqual(normalize("14,80 evra", minimal=True)[0],
                         "štirinajst evrov osemdeset centov")

    def test_no_false_ordinal_warning(self):
        _, warnings = normalize("leta 36.500. Vlak", minimal=True)
        self.assertEqual(warnings, [])


class TestChapterText(unittest.TestCase):
    def test_punctuation_only_is_dropped(self):
        from pipeline import split_sentences
        self.assertEqual(split_sentences("'.."), [])
        self.assertEqual(split_sentences("Konec. .."), ["Konec."])
        self.assertEqual(split_sentences("—"), [])
