from mock import MagicMock
import unittest

from stacker.lookups.handlers.rxref import RxrefLookup
from ....context import Context
from ....config import Config


class TestRxrefHandler(unittest.TestCase):

    def setUp(self):
        self.provider = MagicMock()
        self.context = Context(
            config=Config({"namespace": "ns"})
        )

    def test_rxref_handler(self):
        self.provider.get_output.return_value = "Test Output"

        value = RxrefLookup.handle("fully-qualified-stack-name::SomeOutput",
                                   provider=self.provider,
                                   context=self.context)
        self.assertEqual(value, "Test Output")

        args = self.provider.get_output.call_args
        self.assertEqual(args[0][0], "ns-fully-qualified-stack-name")
        self.assertEqual(args[0][1], "SomeOutput")
