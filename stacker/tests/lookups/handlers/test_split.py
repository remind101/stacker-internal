import unittest

from stacker.lookups.handlers.split import SplitLookup


class TestSplitLookup(unittest.TestCase):
    def test_single_character_split(self):
        value = ",::a,b,c"
        expected = ["a", "b", "c"]
        assert SplitLookup.handle(value) == expected

    def test_multi_character_split(self):
        value = ",,::a,,b,c"
        expected = ["a", "b,c"]
        assert SplitLookup.handle(value) == expected

    def test_invalid_value_split(self):
        value = ",:a,b,c"
        with self.assertRaises(ValueError):
            SplitLookup.handle(value)
