#!/usr/bin/env python3
"""Compile one Papyrus PSC with Caprica for Skyrim or Bethesda's compiler for Starfield."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

LEADING_ZERO_INTEGER = re.compile(r"(?<![A-Za-z0-9_.])0[0-9]+(?![A-Za-z0-9_.])")
QUALIFIED_NAME = r"[A-Za-z_][A-Za-z0-9_]*(?::[A-Za-z_][A-Za-z0-9_]*)*"
SCRIPT_DECLARATION = re.compile(rf"(?im)^\s*scriptname\s+({QUALIFIED_NAME})\b")
STATE_DECLARATION = re.compile(r"(?i)^\s*(?:auto\s+)?state\s+([A-Za-z_][A-Za-z0-9_]*)\b")
END_STATE = re.compile(r"(?i)^\s*endstate\b")
PROPERTY_DECLARATION = re.compile(
    rf"(?i)^\s*{QUALIFIED_NAME}(?:\s*\[\s*\])?\s+"
    r"property\s+[A-Za-z_][A-Za-z0-9_]*\b(?P<tail>.*)$"
)
END_PROPERTY = re.compile(r"(?i)^\s*endproperty\b")
AUTO_PROPERTY = re.compile(r"(?i)\bauto(?:readonly)?\b")
CALLABLE_DECLARATION = re.compile(
    rf"(?i)^\s*(?:{QUALIFIED_NAME}(?:\s*\[\s*\])?\s+)?"
    r"(function|event)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)


class CompileError(Exception):
    pass


def fail(message: str) -> NoReturn:
    raise CompileError(message)


def file_path(path: Path, label: str) -> Path:
    path = path.resolve()
    if not path.is_file():
        fail(f"{label} is not a file: {path}")
    return path


def directory_path(path: Path, label: str) -> Path:
    path = path.resolve()
    if not path.is_dir():
        fail(f"{label} is not a directory: {path}")
    return path


def installed_source_directory(variable: str, relative: str) -> Path:
    raw_root = os.environ.get(variable)
    if not raw_root:
        fail(f"{variable} is unset. Run the script through 'mise exec --'.")
    return directory_path(Path(raw_root) / Path(relative), f"{variable} source directory")


def mask_strings_and_comments(text: str) -> str:
    result: list[str] = []
    state = "code"
    escaped = False
    index = 0

    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if state == "line-comment":
            if char in "\r\n":
                state = "code"
                result.append(char)
            else:
                result.append(" ")
            index += 1
            continue

        if state == "block-comment":
            if char == "/" and next_char == ";":
                state = "code"
                result.extend((" ", " "))
                index += 2
            else:
                result.append(char if char in "\r\n" else " ")
                index += 1
            continue

        if state == "brace-comment":
            if char == "}":
                state = "code"
                result.append(" ")
            else:
                result.append(char if char in "\r\n" else " ")
            index += 1
            continue

        if state == "string":
            result.append(char if char in "\r\n" else " ")
            if char == '"' and not escaped:
                state = "code"
            if char == "\\" and not escaped:
                escaped = True
            else:
                escaped = False
            index += 1
            continue

        if char == ";" and next_char == "/":
            state = "block-comment"
            result.extend((" ", " "))
            index += 2
        elif char == ";":
            state = "line-comment"
            result.append(" ")
            index += 1
        elif char == "{":
            state = "brace-comment"
            result.append(" ")
            index += 1
        elif char == '"':
            state = "string"
            escaped = False
            result.append(" ")
            index += 1
        else:
            result.append(char)
            index += 1

    return "".join(result)


def line_and_column(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    previous_newline = text.rfind("\n", 0, offset)
    column = offset + 1 if previous_newline < 0 else offset - previous_newline
    return line, column


def preflight(source: Path, game: str) -> str:
    data = source.read_bytes()
    errors: list[str] = []

    has_bom = data.startswith(b"\xef\xbb\xbf")
    if has_bom and game == "skyrim":
        errors.append("1:1: save the source as UTF-8 without BOM")

    try:
        text = data.decode("utf-8-sig" if has_bom else "utf-8")
    except UnicodeDecodeError as error:
        errors.append(f"byte {error.start}: save the source as UTF-8")
        text = data.decode("utf-8", errors="replace")

    masked = mask_strings_and_comments(text)

    if game == "skyrim":
        for match in LEADING_ZERO_INTEGER.finditer(masked):
            line, column = line_and_column(masked, match.start())
            errors.append(
                f"{line}:{column}: replace leading-zero integer '{match.group(0)}'; "
                "Caprica parses it as octal"
            )

    script_names = SCRIPT_DECLARATION.findall(masked)
    if len(script_names) != 1:
        errors.append(f"expected one Scriptname declaration; found {len(script_names)}")
        script_name = source.stem
    else:
        script_name = script_names[0]
        parts = script_name.split(":")
        actual = source.with_suffix("").parts[-len(parts):]
        if tuple(part.casefold() for part in actual) != tuple(part.casefold() for part in parts):
            errors.append(f"Scriptname '{script_name}' requires a source path ending in {'/'.join(parts)}.psc")

    state = ""
    in_full_property = False
    declarations: dict[tuple[str, str], tuple[int, str]] = {}
    for line_number, line_text in enumerate(masked.splitlines(), 1):
        if in_full_property:
            if END_PROPERTY.match(line_text):
                in_full_property = False
            continue

        property_match = PROPERTY_DECLARATION.match(line_text)
        if property_match:
            tail = property_match.group("tail")
            in_full_property = "=" not in tail and not AUTO_PROPERTY.search(tail)
            continue

        state_match = STATE_DECLARATION.match(line_text)
        if state_match:
            state = state_match.group(1).casefold()
            continue
        if END_STATE.match(line_text):
            state = ""
            continue

        callable_match = CALLABLE_DECLARATION.match(line_text)
        if not callable_match:
            continue
        kind = callable_match.group(1)
        name = callable_match.group(2)
        key = (state, name.casefold())
        previous = declarations.get(key)
        if previous:
            state_name = state or "<empty state>"
            errors.append(
                f"{line_number}: duplicate {kind} '{name}' in state {state_name}; "
                f"first declaration is on line {previous[0]}"
            )
        else:
            declarations[key] = (line_number, kind)

    if errors:
        details = "\n".join(f"  {source}:{error}" for error in errors)
        fail(f"PSC preflight failed:\n{details}")

    return script_name


def output_file(directory: Path, script_name: str) -> Path:
    *namespace, script_name = script_name.split(":")
    directory = directory.joinpath(*namespace)
    expected = directory / f"{script_name}.pex"
    if expected.exists():
        return expected
    for candidate in directory.glob("*.pex"):
        if candidate.stem.casefold() == script_name.casefold():
            return candidate
    return expected


def install_output(source: Path, destination: Path) -> None:
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        os.close(descriptor)
    except OSError as error:
        fail(f"could not create a temporary output file in {destination.parent}: {error}")

    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    except OSError as error:
        fail(f"could not write output PEX {destination}: {error}")
    finally:
        temporary.unlink(missing_ok=True)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="PSC source file")
    parser.add_argument("--game", choices=("skyrim", "starfield"), required=True, help="PEX target game")
    parser.add_argument("-o", "--output", type=Path, required=True, help="PEX output directory")
    parser.add_argument(
        "-i",
        "--import-dir",
        action="append",
        type=Path,
        default=[],
        help="PSC import directory; repeat in precedence order",
    )
    parser.add_argument("--flags", type=Path, help="custom Papyrus flags file")
    parser.add_argument("--force", action="store_true", help="replace an existing PEX for this script")
    return parser.parse_args()


def main() -> int:
    try:
        args = arguments()
        source = file_path(args.source, "source")
        if source.suffix.casefold() != ".psc":
            fail(f"source must have a .psc extension: {source}")

        script_name = preflight(source, args.game)
        if args.game == "skyrim":
            vanilla_sources = installed_source_directory("TESV_SCRIPTS_ROOT", "Base")
            flags_name = "TESV_Papyrus_Flags.flg"
            caprica = shutil.which("Caprica.exe")
            if not caprica:
                fail("Caprica.exe is unavailable. Run the script through 'mise exec --'.")
            compiler = Path(caprica)
        else:
            vanilla_sources = installed_source_directory("STARFIELD_SCRIPTS_ROOT", "Source")
            flags_name = "Starfield_Papyrus_Flags.flg"
            compiler = file_path(
                vanilla_sources.parent / "bin/PapyrusCompiler/PapyrusCompiler.exe", "Starfield compiler"
            )
        flags = file_path(args.flags or vanilla_sources / flags_name, "flags file")

        source_directory = source.parents[len(script_name.split(":")) - 1]
        vanilla_key = os.path.normcase(str(vanilla_sources))

        ordered_imports = [source_directory]
        seen_imports = {os.path.normcase(str(source_directory))}
        for path in args.import_dir:
            import_directory = directory_path(path, "import directory")
            key = os.path.normcase(str(import_directory))
            if key not in seen_imports and key != vanilla_key:
                ordered_imports.append(import_directory)
                seen_imports.add(key)
        if vanilla_key not in seen_imports:
            ordered_imports.append(vanilla_sources)

        output_directory = args.output.resolve()
        if output_directory.exists() and not output_directory.is_dir():
            fail(f"output path is not a directory: {output_directory}")
        output_directory.mkdir(parents=True, exist_ok=True)

        pex = output_file(output_directory, script_name)
        if pex.exists() and not args.force:
            fail(f"output already exists; pass --force to replace it: {pex}")

        print(f"Vanilla dependency set: {vanilla_sources}")
        print("Import order:")
        for import_directory in ordered_imports:
            print(f"  {import_directory}")

        with tempfile.TemporaryDirectory(prefix="ce-psc-") as temporary_directory:
            build_directory = Path(temporary_directory)
            if args.game == "skyrim":
                command = [
                    str(compiler), "--game", "skyrim", "--ignorecwd",
                    "--flags", str(flags), "--output", str(build_directory),
                ]
                for import_directory in ordered_imports:
                    command.extend(("--import", str(import_directory)))
                command.append(str(source))
            else:
                command = [
                    str(compiler), script_name, "-ignorecwd",
                    f"-i={';'.join(str(path) for path in ordered_imports)}",
                    f"-f={flags}", f"-o={build_directory}",
                ]

            print(f"Running: {subprocess.list2cmdline(command)}", flush=True)
            result = subprocess.run(command)

            built_pex = output_file(build_directory, script_name)
            if result.returncode != 0:
                fail(f"{compiler.name} failed with exit code {result.returncode}")
            if not built_pex.is_file() or built_pex.stat().st_size == 0:
                fail(f"{compiler.name} returned success without a non-empty PEX: {built_pex}")

            size = built_pex.stat().st_size
            digest = hashlib.sha256(built_pex.read_bytes()).hexdigest()
            install_output(built_pex, pex)

        print(f"Created: {pex}")
        print(f"Size: {size} bytes")
        print(f"SHA256: {digest}")
        return 0
    except CompileError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
