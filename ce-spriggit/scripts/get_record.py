#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, TextIO

from spriggit_tree import (
    FORM_KEY,
    RecordObject,
    SpriggitTree,
    SpriggitTreeError,
    native_path,
)


class RecordLookupError(RuntimeError):
    pass


def record_location(item: RecordObject) -> str:
    path = json.dumps(list(item.path), ensure_ascii=False, separators=(",", ":"))
    return f"{item.source.as_posix()} path={path}"


def validate_form_key(form_key: str, location: str = "") -> None:
    if not FORM_KEY.fullmatch(form_key):
        raise RecordLookupError(
            f"invalid FormKey {form_key!r}{location}. Expected 000000:Plugin.ext"
        )


def record_result(item: RecordObject) -> dict[str, Any]:
    return {
        "source": item.source.as_posix(),
        "path": list(item.path),
        "record": item.data,
    }


def get_records(root: Path, form_keys: Iterable[str]) -> list[dict[str, Any]]:
    requested = list(form_keys)
    if not requested:
        raise RecordLookupError("no FormKeys supplied")

    first_position: dict[str, int] = {}
    for position, form_key in enumerate(requested, start=1):
        validate_form_key(form_key)
        folded = form_key.casefold()
        if folded in first_position:
            raise RecordLookupError(
                f"duplicate requested FormKey at position {position}: {form_key} "
                f"(first supplied at position {first_position[folded]})"
            )
        first_position[folded] = position

    matches: dict[str, list[RecordObject]] = {
        folded: [] for folded in first_position
    }
    for item in SpriggitTree(root).records():
        folded = item.data["FormKey"].casefold()
        if folded in matches:
            matches[folded].append(item)

    results: list[dict[str, Any]] = []
    for form_key in requested:
        found = matches[form_key.casefold()]
        if not found:
            raise RecordLookupError(f"record not found: {form_key}")
        if len(found) > 1:
            locations = " | ".join(record_location(item) for item in found)
            raise RecordLookupError(
                f"multiple records found for {form_key}: {locations}"
            )
        results.append(record_result(found[0]))
    return results


def get_record(root: Path, form_key: str) -> dict[str, Any]:
    return get_records(root, [form_key])[0]


def parse_form_key_lines(lines: Iterable[str]) -> list[str]:
    form_keys: list[str] = []
    first_line_by_key: dict[str, int] = {}

    for line_number, raw_line in enumerate(lines, start=1):
        form_key = raw_line.strip()
        if line_number == 1:
            form_key = form_key.lstrip("\ufeff")
        location = f" on input line {line_number}"
        if not form_key:
            raise RecordLookupError(f"empty FormKey{location}")
        validate_form_key(form_key, location)

        folded = form_key.casefold()
        if folded in first_line_by_key:
            raise RecordLookupError(
                f"duplicate FormKey{location}: {form_key} "
                f"(first supplied on line {first_line_by_key[folded]})"
            )
        first_line_by_key[folded] = line_number
        form_keys.append(form_key)

    if not form_keys:
        raise RecordLookupError("FormKey input contains no entries")
    return form_keys


def read_form_keys(source: str, stdin: TextIO) -> list[str]:
    if source == "-":
        return parse_form_key_lines(stdin)

    path = Path(source)
    try:
        with open(native_path(path), encoding="utf-8-sig") as stream:
            return parse_form_key_lines(stream)
    except OSError as error:
        raise RecordLookupError(f"cannot read FormKey input {path}: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Get complete major records from a Spriggit JSON tree."
    )
    parser.add_argument("input", type=Path, help="Spriggit output directory")
    parser.add_argument(
        "form_key",
        nargs="?",
        help="FormKey in 000000:Plugin.ext format",
    )
    parser.add_argument(
        "--formkeys-from",
        metavar="<path|->",
        help="read one FormKey per line; use - for standard input",
    )
    args = parser.parse_args()

    if (args.form_key is None) == (args.formkeys_from is None):
        parser.error("supply one FormKey or --formkeys-from <path|->")

    batch = args.formkeys_from is not None
    try:
        if batch:
            form_keys = read_form_keys(args.formkeys_from, sys.stdin)
        else:
            form_keys = [args.form_key]
        results = get_records(args.input, form_keys)
    except (RecordLookupError, SpriggitTreeError) as error:
        parser.exit(1, f"error: {error}\n")

    if batch:
        output = "".join(
            json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"
            for result in results
        )
    else:
        output = json.dumps(results[0], indent=2, ensure_ascii=False) + "\n"
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
