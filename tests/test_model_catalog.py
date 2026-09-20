import json
from pathlib import Path
import unittest


class ModelCatalogTests(unittest.TestCase):
    def test_catalog_only_contains_pinned_model_data(self):
        catalog = json.loads((Path(__file__).resolve().parents[1] / "models/catalog.json").read_text())
        self.assertEqual(catalog["schema"], 1)
        self.assertEqual(catalog["runtime"], "gemma4-mlx-vlm-0.6.17-v1")
        self.assertGreater(len(catalog["models"]), 0)
        for model in catalog["models"]:
            self.assertEqual(model["repo"], "mlx-community/gemma-4-e4b-it-4bit")
            self.assertRegex(model["revision"], r"^[0-9a-f]{40}$")
            self.assertTrue({"config.json", "model.safetensors", "tokenizer.json"} <= model["files"].keys())
            for name, spec in model["files"].items():
                self.assertEqual(Path(name).name, name)
                self.assertTrue(name.endswith((".json", ".jinja", ".safetensors", ".model")))
                self.assertIs(type(spec["size"]), int)
                self.assertGreater(spec["size"], 0)
                self.assertRegex(spec["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__": unittest.main()
