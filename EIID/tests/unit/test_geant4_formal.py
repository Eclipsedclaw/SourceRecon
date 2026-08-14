import unittest

from eiid.detector import ChannelMapping
from eiid.io import FormalGeant4RootEventSource


class FormalGeant4InputTests(unittest.TestCase):
    def test_branch_contract_requires_primary_and_deposit_identity(self):
        mapping = ChannelMapping({0: "ch2", 1: "ch1", 2: "ch0"}, {"ch2": 0, "ch1": 1, "ch0": 2})
        with self.assertRaises(ValueError):
            FormalGeant4RootEventSource(
                "missing.root", "PrimaryTruth", "DetectorDeposit",
                primary_branches={"event_id": "eventID"},
                deposit_branches={"event_id": "eventID"},
                mapping=mapping, dataset_id="formal",
            )


if __name__ == "__main__":
    unittest.main()
