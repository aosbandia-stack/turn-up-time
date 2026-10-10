import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts/tool_runtime_catalog.py"
spec = importlib.util.spec_from_file_location("tool_runtime_catalog", MODULE)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

class RuntimeInventoryTests(unittest.TestCase):
    def test_interpreter_exclusion_keeps_new_parent_code_visible(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as meta:
            root = Path(tmp)
            (root / "Lib/site-packages").mkdir(parents=True)
            (root / "Lib/os.py").write_text("stdlib")
            (root / "Lib/site-packages/unreachable.py").write_text("excluded")
            inventory = Path(meta) / "inventory.json"
            runtime.write_inventory(inventory, root, ["."], "test", [".git", "Lib/site-packages"])
            reference = runtime.ref(inventory)
            self.assertEqual(runtime.verify_inventory(reference, "test", interpreter=True), 1)
            with self.assertRaises(ValueError):
                runtime.verify_inventory(reference, "test")
            (root / "Lib/sitecustomize.py").write_text("new startup code")
            with self.assertRaises(ValueError):
                runtime.verify_inventory(reference, "test", interpreter=True)

    def test_drift_and_unlisted_code_including_bytecode_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "payload").mkdir()
            asset = root / "payload/module.py"
            asset.write_text("original")
            inventory = root / "inventory.json"
            runtime.write_inventory(inventory, root, ["payload"], "test")
            reference = runtime.ref(inventory)
            self.assertEqual(runtime.verify_inventory(reference, "test"), 1)
            (root / "payload/cache.pyc").write_bytes(b"cache")
            with self.assertRaises(ValueError):
                runtime.verify_inventory(reference, "test")
            (root / "payload/cache.pyc").unlink()
            injected = root / "payload/injected.py"
            injected.write_text("unlisted")
            with self.assertRaises(ValueError):
                runtime.verify_inventory(reference, "test")
            injected.unlink()
            asset.write_text("changed")
            with self.assertRaises(ValueError):
                runtime.verify_inventory(reference, "test")

    def test_scope_escape_collision_and_metadata_drift_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "asset").write_text("safe")
            for scopes in (["../escape"], ["asset", "asset"], ["missing"]):
                with self.assertRaises(ValueError):
                    runtime.enumerate_files(root, scopes)
            inventory = root / "inventory.json"
            runtime.write_inventory(inventory, root, ["asset"], "test")
            reference = runtime.ref(inventory)
            with self.assertRaises(ValueError):
                runtime.verify_inventory(reference, "wrong-runtime")
            inventory.write_text("{}")
            with self.assertRaises(ValueError):
                runtime.verify_inventory(reference, "test")

if __name__ == "__main__":
    unittest.main()
