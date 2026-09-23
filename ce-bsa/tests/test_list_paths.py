from __future__ import annotations

import errno
import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

_SCRIPT = Path(__file__).parents[1] / "scripts" / "list_paths.py"
_SPEC = importlib.util.spec_from_file_location("list_paths", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

ListOutputError = _MODULE.ListOutputError
parse_list_output = _MODULE.parse_list_output
write_paths = _MODULE.write_paths


class _ErrorStream:
    def __init__(self, error: OSError) -> None:
        self.error = error

    def write(self, _text: str) -> int:
        raise self.error

    def flush(self) -> None:
        raise self.error


class ParseListOutputTests(unittest.TestCase):
    def test_parses_bsa_output_and_ignores_banner_url(self) -> None:
        output = """
BSArch v0.9c x64
https://mozilla.org/MPL/2.0/.

  Archive Name: example.bsa
        Format: Skyrim SE, Skyrim AE
         Files: 2
 Archive Flags: 0x00000003          File Flags: 0x00000000
                *Include Directory Names         Meshes
                *Include File Names              Textures

meshes\\example.nif
interface\\Folder With Spaces\\Menu.swf
"""

        self.assertEqual(
            parse_list_output(output),
            ["meshes/example.nif", "interface/Folder With Spaces/Menu.swf"],
        )

    def test_parses_ba2_output(self) -> None:
        output = """
BSArch v0.9c x64

  Archive Name: example.ba2
        Format: Fallout 4
         Files: 1

Textures\\Example.DDS
"""

        self.assertEqual(parse_list_output(output), ["Textures/Example.DDS"])

    def test_parses_empty_archive(self) -> None:
        output = """
BSArch v0.9c x64

  Archive Name: empty.ba2
        Format: Fallout 4
         Files: 0

"""

        self.assertEqual(parse_list_output(output), [])

    def test_requires_file_count(self) -> None:
        with self.assertRaisesRegex(ListOutputError, "no 'Files:' count"):
            parse_list_output("BSArch v0.9c x64\n")

    def test_rejects_count_mismatch(self) -> None:
        output = """
  Archive Name: example.ba2
         Files: 2

one.txt
"""

        with self.assertRaisesRegex(
            ListOutputError, "declared 2 files but listed 1"
        ):
            parse_list_output(output)

    def test_requires_blank_line_before_file_list(self) -> None:
        output = "  Archive Name: example.ba2\n         Files: 1\none.txt\n"

        with self.assertRaisesRegex(ListOutputError, "no blank line"):
            parse_list_output(output)


class WritePathsTests(unittest.TestCase):
    def test_handles_broken_pipe(self) -> None:
        stream = _ErrorStream(BrokenPipeError())

        with (
            mock.patch.object(_MODULE.sys, "stdout", stream),
            mock.patch.object(_MODULE, "_redirect_stdout_to_null") as redirect,
        ):
            write_paths(["one.txt"])

        redirect.assert_called_once_with()

    @unittest.skipUnless(os.name == "nt", "Windows reports a closed pipe as EINVAL")
    def test_handles_windows_closed_pipe(self) -> None:
        stream = _ErrorStream(OSError(errno.EINVAL, "Invalid argument"))

        with (
            mock.patch.object(_MODULE.sys, "stdout", stream),
            mock.patch.object(_MODULE, "_redirect_stdout_to_null") as redirect,
        ):
            write_paths(["one.txt"])

        redirect.assert_called_once_with()

    def test_raises_other_output_errors(self) -> None:
        stream = _ErrorStream(OSError(errno.EIO, "I/O error"))

        with mock.patch.object(_MODULE.sys, "stdout", stream):
            with self.assertRaises(OSError) as raised:
                write_paths(["one.txt"])

        self.assertEqual(raised.exception.errno, errno.EIO)


if __name__ == "__main__":
    unittest.main()
