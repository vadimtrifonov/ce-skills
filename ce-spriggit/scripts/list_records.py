#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from spriggit_tree import RecordObject, SpriggitTree, SpriggitTreeError


# Group names that do not map to record types by regular singularization.
ROOT_TYPE_OVERRIDES = {
    "Actions": "ActionRecord",
    "AlchemicalApparatuses": "AlchemicalApparatus",
    "BodyParts": "BodyPartData",
    "Clouds": "Clouds",
    "Colors": "ColorRecord",
    "Debris": "Debris",
    "Eyes": "Eyes",
    "Florae": "Flora",
    "InstanceNamingRules": "InstanceNamingRules",
    "ObjectModifications": "AObjectModification",
    "ReverbParameters": "ReverbParameters",
    "TimeOfDays": "TimeOfDayRecord",
    "WordsOfPower": "WordOfPower",
}


class RecordListError(RuntimeError):
    pass


def singularize(category: str) -> str:
    if category.endswith(("sses", "shes", "ches", "xes")):
        return category[:-2]
    if category.endswith("ies"):
        return category[:-3] + "y"
    if category.endswith("s"):
        return category[:-1]
    return category


def root_record_type(relative_parts: tuple[str, ...]) -> str:
    category = relative_parts[0]
    if category == "Quests" and len(relative_parts) > 3:
        category = relative_parts[2]
    if category == "DialogTopics" and relative_parts[-2] == "Responses":
        return "DialogResponses"
    if category == "Worldspaces" and len(relative_parts) > 3:
        return "Cell"
    return ROOT_TYPE_OVERRIDES.get(category, singularize(category))


def record_type(record: dict[str, Any], relative_parts: tuple[str, ...], pointer: tuple[Any, ...]) -> str:
    explicit = record.get("MutagenObjectType")
    if isinstance(explicit, str) and explicit:
        return explicit

    if not pointer:
        return root_record_type(relative_parts)

    field_names = [part for part in pointer if isinstance(part, str)]
    if field_names and field_names[-1] == "TopCell":
        return "Cell"
    if field_names and field_names[-1] == "Landscape":
        return "Landscape"
    if "NavigationMeshes" in field_names:
        return "NavigationMesh"

    location = ".".join(str(part) for part in pointer)
    raise RecordListError(
        f"cannot infer the record type at {'/'.join(relative_parts)}:{location}"
    )


def is_deleted(record: dict[str, Any]) -> bool:
    for field in ("SkyrimMajorRecordFlags", "StarfieldMajorRecordFlags"):
        flags = record.get(field, [])
        if isinstance(flags, str):
            flags = [flags]
        if isinstance(flags, list) and any(
            isinstance(flag, str) and flag.casefold() == "deleted" for flag in flags
        ):
            return True

    raw = record.get("MajorRecordFlagsRaw")
    try:
        raw_value = int(raw, 0) if isinstance(raw, str) else int(raw)
    except (TypeError, ValueError):
        return False
    return bool(raw_value & 0x20)


def record_row(item: RecordObject, mod_key: str) -> dict[str, Any]:
    record = item.data
    form_key = record["FormKey"]
    _, owner = form_key.split(":", 1)
    editor_id = record.get("EditorID")
    return {
        "type": record_type(record, item.source.parts, item.path),
        "formKey": form_key,
        "editorId": editor_id if isinstance(editor_id, str) else None,
        "kind": "new" if owner.casefold() == mod_key.casefold() else "override",
        "deleted": is_deleted(record),
    }


def list_records(root: Path) -> list[dict[str, Any]]:
    tree = SpriggitTree(root)
    records = [record_row(item, tree.mod_key) for item in tree.records()]
    records.sort(
        key=lambda record: (
            record["type"].casefold(),
            record["formKey"].casefold(),
            (record["editorId"] or "").casefold(),
        )
    )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List every major record in a Spriggit JSON tree as JSONL."
    )
    parser.add_argument("input", type=Path, help="Spriggit output directory")
    args = parser.parse_args()

    try:
        records = list_records(args.input)
    except (RecordListError, SpriggitTreeError) as error:
        parser.exit(1, f"error: {error}\n")

    for record in records:
        sys.stdout.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
