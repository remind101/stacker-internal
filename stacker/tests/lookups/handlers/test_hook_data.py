import unittest


from stacker.context import Context
from stacker.lookups.handlers.hook_data import HookDataLookup


class TestHookDataLookup(unittest.TestCase):

    def setUp(self):
        self.ctx = Context({"namespace": "test-ns"})
        self.ctx.set_hook_data("fake_hook", {"result": "good"})

    def test_valid_hook_data(self):
        value = HookDataLookup.handle("fake_hook::result", context=self.ctx)
        self.assertEqual(value, "good")

    def test_invalid_hook_data(self):
        with self.assertRaises(KeyError):
            HookDataLookup.handle("fake_hook::bad_key", context=self.ctx)

    def test_bad_value_hook_data(self):
        with self.assertRaises(ValueError):
            HookDataLookup.handle("fake_hook", context=self.ctx)
