import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_nif.py"
_SPEC = importlib.util.spec_from_file_location("render_nif", _SCRIPT)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class AssetQueryTests(unittest.TestCase):
    def test_prevents_console_reattachment_without_changing_parent_environment(self):
        for parent in ({"PATH": "tools"}, {"PATH": "tools", "TERM": "xterm"}):
            with self.subTest(parent=parent):
                with mock.patch.dict(_MODULE.os.environ, parent, clear=True):
                    with mock.patch.object(_MODULE.subprocess, "run") as run:
                        _MODULE.run_tool(["nif_info.exe", "-q"], 10)
                    child = run.call_args.kwargs["env"]
                    self.assertEqual(child["TERM"], parent.get("TERM", "dumb"))
                    self.assertEqual(child["PATH"], "tools")
                    self.assertEqual(dict(_MODULE.os.environ), parent)

    def test_requires_one_exact_match(self):
        for text, valid in (
            ("Author\tmeshes/model.nif\t123\n", True),
            ("", False),
            ("Author\tmeshes/model.nif\t123\nAuthor\tmeshes/model.nif.copy.nif\t456\n", False),
        ):
            with self.subTest(text=text):
                process = subprocess.CompletedProcess([], 0, text, "")
                with mock.patch.object(_MODULE, "run_tool", return_value=process):
                    args = (Path("nif_info.exe"), Path("Data"), "meshes/model.nif", 10)
                    if valid:
                        asset, query = _MODULE.require_exact_asset(*args)
                        self.assertEqual(asset["size"], 123)
                        self.assertEqual(query["return_code"], 0)
                    else:
                        with self.assertRaisesRegex(_MODULE.RenderError, "exactly one exact NIF"):
                            _MODULE.require_exact_asset(*args)


if __name__ == "__main__":
    unittest.main()
