"""Regression tests for the Python generator embedded in the Coco Preview workflow."""

import json
import os
import runpy
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "coco_preview.yaml"


class CocoPreviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.output = Path(cls.temporary.name) / "preview"
        # Execute the actual workflow code, including its entry point, without
        # maintaining a second copy or introducing a YAML parser dependency.
        workflow = WORKFLOW.read_text(encoding="utf-8")
        script = textwrap.dedent(
            workflow.split("          python <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
        )
        script_path = Path(cls.temporary.name) / "coco_preview.py"
        script_path.write_text(script, encoding="utf-8")
        with mock.patch.dict(
            os.environ,
            {"GITHUB_WORKSPACE": str(ROOT), "PREVIEW_DIR": str(cls.output)},
        ):
            cls.generator = runpy.run_path(str(script_path))

    def test_uses_current_source_annotations(self):
        self.assertEqual(
            ROOT / "ok_templates" / "coco_annotations.json",
            self.generator["ANNOTATIONS_PATH"],
        )

    def test_generates_every_exported_template_and_index(self):
        previews = self.generator["previews"]
        templates = {path.name for path in (ROOT / "assets" / "templates").glob("*.png")}
        self.assertTrue(templates)
        self.assertEqual(
            templates, {Path(item.source_image).name for item in previews}
        )
        annotations = json.loads(
            self.generator["ANNOTATIONS_PATH"].read_text(encoding="utf-8")
        )
        self.assertEqual(len(annotations["annotations"]), len(previews))
        outputs = {item.output_name for item in previews}
        self.assertEqual(len(previews), len(outputs))
        self.assertEqual(outputs, {path.name for path in self.output.glob("*.png")})
        index = (self.output / "index.html").read_text(encoding="utf-8")
        for name in outputs:
            self.assertIn(name, index)

    def test_fractional_cloud_bbox_uses_exported_template(self):
        # A fixed fixture reproduces this release's regression without requiring
        # future upstream releases to retain these exact cloud templates.
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            templates = assets / "templates"
            templates.mkdir(parents=True)
            annotations_path = root / "ok_templates" / "coco_annotations.json"
            annotations_path.parent.mkdir()
            annotations_path.write_text(json.dumps({
                "categories": [{"id": 302, "name": "has_target_cloud"}],
                "images": [{"id": 310, "width": 1920, "height": 1080}],
                "annotations": [{
                    "id": 463, "category_id": 302, "image_id": 310,
                    "bbox": [1433.9176432940983, 958.6137615730172,
                             30.623501318268836, 29.10609791183913],
                }],
            }), encoding="utf-8")
            filename = "has_target_cloud_1920x1080_1434_959.png"
            with Image.new("RGB", (31, 29)) as crop:
                crop.save(templates / filename)
            previews = self.generator["generate_previews"](
                annotations_path, assets, root / "out"
            )
            self.assertEqual(1, len(previews))
            self.assertEqual(f"templates/{filename}", previews[0].source_image)
            self.assertEqual((31, 29), (previews[0].width, previews[0].height))
            self.assertTrue((root / "out" / previews[0].output_name).is_file())

    def test_coordinate_rounding_matches_exporter_including_half_even(self):
        clamp_bbox = self.generator["clamp_bbox"]
        self.assertEqual((13, 25, 19, 32), clamp_bbox([12.75, 24.6, 6.1, 7.2], 100, 100))
        self.assertEqual((12, 26, 14, 28), clamp_bbox([12.5, 25.5, 1, 3], 100, 100))

    def test_missing_templates_are_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                self.generator["generate_previews"](
                    self.generator["ANNOTATIONS_PATH"],
                    root / "missing-assets",
                    root / "preview",
                )


if __name__ == "__main__":
    unittest.main()
