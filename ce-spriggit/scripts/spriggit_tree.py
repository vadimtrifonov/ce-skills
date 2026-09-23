import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


FORM_KEY = re.compile(r"^[0-9A-Fa-f]{6}:.+$")
IGNORED_JSON_FILES = {"GroupRecordData.json", "spriggit-meta.json"}
JsonPathPart = str | int


class SpriggitTreeError(RuntimeError):
    pass


@dataclass(frozen=True)
class RecordObject:
    source: Path
    path: tuple[JsonPathPart, ...]
    data: dict[str, Any]


def native_path(path: Path) -> str:
    """Return an absolute path that supports long file names on Windows."""
    absolute = os.path.abspath(os.fspath(path))
    if os.name != "nt" or absolute.startswith("\\\\?\\"):
        return absolute
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute


def load_json(path: Path) -> Any:
    try:
        with open(native_path(path), encoding="utf-8") as stream:
            return json.load(stream)
    except json.JSONDecodeError as error:
        raise SpriggitTreeError(f"invalid JSON in {path}: {error}") from error
    except OSError as error:
        raise SpriggitTreeError(f"cannot read {path}: {error}") from error


def walk_record_objects(
    value: Any,
    source: Path,
    path: tuple[JsonPathPart, ...] = (),
) -> Iterator[RecordObject]:
    if isinstance(value, dict):
        form_key = value.get("FormKey")
        if isinstance(form_key, str) and FORM_KEY.fullmatch(form_key):
            yield RecordObject(source=source, path=path, data=value)

        for name, child in value.items():
            yield from walk_record_objects(child, source, path + (name,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_record_objects(child, source, path + (index,))


class SpriggitTree:
    def __init__(self, root: Path):
        if not root.is_dir():
            raise SpriggitTreeError(f"input is not a Spriggit directory: {root}")

        metadata_path = root / "RecordData.json"
        if not metadata_path.is_file():
            raise SpriggitTreeError(f"missing root metadata file: {metadata_path}")

        metadata = load_json(metadata_path)
        mod_key = metadata.get("ModKey") if isinstance(metadata, dict) else None
        if not isinstance(mod_key, str) or not mod_key:
            raise SpriggitTreeError(f"missing ModKey in {metadata_path}")

        self.root = root
        self.mod_key = mod_key

    def records(self) -> Iterator[RecordObject]:
        try:
            files = sorted(self.root.rglob("*.json"), key=lambda path: str(path).casefold())
        except OSError as error:
            raise SpriggitTreeError(f"cannot enumerate {self.root}: {error}") from error

        for source_path in files:
            source = source_path.relative_to(self.root)
            if source.parts == ("RecordData.json",):
                continue
            if source_path.name in IGNORED_JSON_FILES:
                continue

            data = load_json(source_path)
            yield from walk_record_objects(data, source)
