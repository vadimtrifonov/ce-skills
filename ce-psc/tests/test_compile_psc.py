import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compile_psc.py"
sys.path.insert(0, str(SCRIPT.parent))
from compile_psc import CompileError, preflight


CAPRICA = shutil.which("Caprica.exe")
TESV_SOURCES = os.environ.get("TESV_SCRIPTS_ROOT")
STARFIELD_SOURCES = os.environ.get("STARFIELD_SCRIPTS_ROOT")


class CompileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ce-psc test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\r\n")
        return path

    def compile(self, game: str, source: Path, *options: str) -> subprocess.CompletedProcess:
        environment = os.environ.copy()
        environment.pop("TESV_SCRIPTS_ROOT" if game == "starfield" else "STARFIELD_SCRIPTS_ROOT", None)
        command = [sys.executable, "-B", str(SCRIPT), str(source), "--game", game,
                   "-o", str(self.root / "output"), *options]
        with subprocess.Popen(command, cwd=self.root, env=environment,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
            try:
                stdout, stderr = process.communicate(timeout=45)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                stdout, stderr = process.communicate()
                self.fail(f"Compiler timed out:\n{stdout}\n{stderr}")
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)

    def test_preflight_handles_namespaced_types_and_property_accessors(self) -> None:
        source = self.write(
            "Example/Main.psc",
            "Scriptname Example:Main\n"
            + "\n".join(
                f"Example:Other Property {name}\n"
                "  Example:Other Function Get()\n"
                "    Return None\n"
                "  EndFunction\n"
                "EndProperty\n"
                for name in ("First", "Second")
            ),
        )
        self.assertEqual(preflight(source, "starfield"), "Example:Main")

    def test_preflight_rejects_invalid_sources(self) -> None:
        cases = [
            ("\ufeffScriptname Main\n", "without BOM"),
            ("Scriptname Main\nInt value = 0124\n", "leading-zero"),
            ("Scriptname Other\n", "source path"),
            ("Scriptname Main\n" + "Function Run()\nEndFunction\n" * 2, "duplicate"),
            ("Scriptname Main\n" + "Example:Other Function Get()\nReturn None\nEndFunction\n" * 2, "duplicate"),
        ]
        for text, error in cases:
            with self.subTest(error=error, text=text):
                source = self.write("Main.psc", text)
                with self.assertRaisesRegex(CompileError, error):
                    preflight(source, "skyrim")

    @unittest.skipUnless(CAPRICA and TESV_SOURCES and STARFIELD_SOURCES, "run through the skill's mise environment")
    def test_game_headers_and_import_precedence(self) -> None:
        override = self.write(
            "override/Dependency.psc",
            "Scriptname Dependency\nInt Function Value() Global Native\n",
        )
        baseline = self.write(
            "baseline/Dependency.psc",
            "Scriptname Dependency\nInt Function Value(Int required) Global Native\n",
        )
        self.write("Dependency.psc", "Scriptname Dependency\nInt Function Value(Int wrongCwd) Global Native\n")
        for game, header in (("skyrim", "fa57c0de03020001"), ("starfield", "dec057fa030c0400")):
            with self.subTest(game=game):
                name = f"Smoke_{game}"
                source = self.write(
                    f"source/{name}.psc",
                    f"Scriptname {name} extends Quest\nInt Function Answer()\n"
                    "  Return GetStage() + Dependency.Value()\nEndFunction\n",
                )
                result = self.compile(game, source, "-i", str(override.parent), "-i", str(baseline.parent))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                pex = self.root / "output" / f"{name}.pex"
                self.assertEqual(pex.read_bytes()[:8], bytes.fromhex(header))

    @unittest.skipUnless(STARFIELD_SOURCES, "run through the skill's mise environment")
    def test_starfield_namespaced_output_and_custom_flags(self) -> None:
        self.write("base/Example/Dependency.psc",
                   "Scriptname Example:Dependency\nInt Function Value() Global Native\n")
        self.write("source/Example/Local.psc",
                   "Scriptname Example:Local\nInt Function Value() Global Native\n")
        self.write("base/Example/Local.psc",
                   "Scriptname Example:Local\nInt Function Value(Int required) Global Native\n")
        default_flags = Path(STARFIELD_SOURCES) / "Source/Starfield_Papyrus_Flags.flg"
        flags = self.write("custom.flg", default_flags.read_text(encoding="utf-8") + "\nFlag ScriptTag 7 { Script }\n")
        source = self.write(
            "source/Example/Nested/Main.psc",
            "\ufeff\nScriptname Example:Nested:Main ScriptTag\n"
            "Int Function Answer() Global\n"
            "  Return Example:Dependency.Value() + Example:Local.Value() + 0124\nEndFunction\n",
        )
        original_source = source.read_bytes()
        result = self.compile("starfield", source, "-i", str(self.root / "base"), "--flags", str(flags))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(source.read_bytes(), original_source)
        pex = self.root / "output/Example/Nested/Main.pex"
        self.assertEqual(pex.read_bytes()[:8], bytes.fromhex("dec057fa030c0400"))
        self.assertEqual(list((self.root / "output").rglob("*.pex")), [pex])

    @unittest.skipUnless(CAPRICA and TESV_SOURCES and STARFIELD_SOURCES, "run through the skill's mise environment")
    def test_replacement_requires_force_and_preserves_output_on_failure(self) -> None:
        for game in ("skyrim", "starfield"):
            with self.subTest(game=game):
                name = f"Replace_{game}"
                relative = f"source/{name}.psc"
                template = f"Scriptname {name}\nInt Function Answer() Global\n  Return {{}}\nEndFunction\n"
                source = self.write(relative, template.format("42"))
                result = self.compile(game, source)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                pex = self.root / "output" / f"{name}.pex"
                original = pex.read_bytes()

                result = self.compile(game, source)
                self.assertEqual(result.returncode, 2)
                self.assertIn("output already exists", result.stderr)
                self.assertEqual(pex.read_bytes(), original)

                self.write(relative, template.format("missingVariable"))
                result = self.compile(game, source, "--force")
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(pex.read_bytes(), original)

                self.write(relative, template.format("43"))
                result = self.compile(game, source, "--force")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotEqual(pex.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
