import copy
import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("validate_protocol", HERE / "validate_protocol.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ValidateProtocolTests(unittest.TestCase):
    def setUp(self):
        self.protocol = MODULE.load_json(HERE / "protocol.json")

    def test_proposal_is_valid_and_non_executable(self):
        result = MODULE.validate(self.protocol)
        self.assertEqual(result["status"], "PROPOSED_NOT_AUTHORIZED")
        self.assertFalse(result["authorized"])
        self.assertIsNone(result["selected_task"])
        self.assertEqual(result["model_cells"], 6)

    def test_duplicate_arm_cell_is_rejected(self):
        changed = copy.deepcopy(self.protocol)
        changed["arm_matrix"][1] = copy.deepcopy(changed["arm_matrix"][0])
        with self.assertRaisesRegex(MODULE.ProtocolError, "arm matrix"):
            MODULE.validate(changed)

    def test_model_change_before_activation_is_rejected(self):
        changed = copy.deepcopy(self.protocol)
        changed["models"][0]["model"] = "unregistered-model"
        with self.assertRaisesRegex(MODULE.ProtocolError, "model slots"):
            MODULE.validate(changed)

    def test_selecting_task_while_proposed_is_rejected(self):
        changed = copy.deepcopy(self.protocol)
        changed["selected_task"] = {"id": "not-authorized"}
        with self.assertRaisesRegex(MODULE.ProtocolError, "schema invalid"):
            MODULE.validate(changed)


if __name__ == "__main__":
    unittest.main()
