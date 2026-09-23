import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import get_record as get_record_module
from get_record import (
    RecordLookupError,
    get_record,
    get_records,
    parse_form_key_lines,
)
from list_records import is_deleted, list_records


class RecordToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "Test.spriggit"
        self.write_json("RecordData.json", {"ModKey": "Test.esp"})
        self.write_json(
            "Quests/TestQuest.json",
            {
                "FormKey": "000001:Test.esp",
                "EditorID": "TestQuest",
                "MajorRecordFlagsRaw": 32,
            },
        )
        self.write_json(
            "Cells/0/0/TestCell/RecordData.json",
            {
                "FormKey": "000100:Skyrim.esm",
                "EditorID": "TestCell",
                "Persistent": [
                    {
                        "MutagenObjectType": "PlacedObject",
                        "FormKey": "000002:Test.esp",
                        "EditorID": "TestReference",
                        "Base": "000001:Test.esp",
                    }
                ],
                "NavigationMeshes": [
                    {
                        "FormKey": "000200:Skyrim.esm",
                    }
                ],
                "LinkedRecord": "000002:Test.esp",
            },
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_json(self, relative_path: str, value: object) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_list_records_keeps_normalized_output(self) -> None:
        records = list_records(self.root)
        self.assertEqual(
            [(item["type"], item["formKey"]) for item in records],
            [
                ("Cell", "000100:Skyrim.esm"),
                ("NavigationMesh", "000200:Skyrim.esm"),
                ("PlacedObject", "000002:Test.esp"),
                ("Quest", "000001:Test.esp"),
            ],
        )
        quest = next(item for item in records if item["type"] == "Quest")
        self.assertEqual(quest["kind"], "new")
        self.assertTrue(quest["deleted"])

    def test_lists_dialogue_layouts_and_starfield_groups(self) -> None:
        cases = [
            ("DialogTopics/Topic/RecordData.json", "DialogTopic"),
            ("DialogTopics/Topic/Responses/Response.json", "DialogResponses"),
            ("Quests/Quest/RecordData.json", "Quest"),
            ("Quests/Quest/DialogTopics/Topic/RecordData.json", "DialogTopic"),
            ("Quests/Quest/DialogTopics/Topic/Responses/Response.json", "DialogResponses"),
            ("Quests/Quest/Scenes/Scene.json", "Scene"),
            ("Clouds/Cloud.json", "Clouds"),
            ("InstanceNamingRules/Rule.json", "InstanceNamingRules"),
            ("ObjectModifications/Modification.json", "AObjectModification"),
            ("TimeOfDays/Time.json", "TimeOfDayRecord"),
        ]
        for index, (path, _) in enumerate(cases, start=0x300):
            self.write_json(path, {"FormKey": f"{index:06X}:Test.esp"})

        records = {item["formKey"]: item for item in list_records(self.root)}
        for index, (path, expected_type) in enumerate(cases, start=0x300):
            with self.subTest(path=path):
                form_key = f"{index:06X}:Test.esp"
                self.assertEqual(records[form_key]["type"], expected_type)
                self.assertEqual(get_record(self.root, form_key)["source"], path)

    def test_recognizes_game_specific_deleted_flags(self) -> None:
        for field in ("SkyrimMajorRecordFlags", "StarfieldMajorRecordFlags"):
            for flags in ("Deleted", ["Compressed", "Deleted"]):
                with self.subTest(field=field, flags=flags):
                    self.assertTrue(is_deleted({field: flags}))
            self.assertFalse(is_deleted({field: ["Compressed"]}))

    def test_gets_top_level_and_embedded_records(self) -> None:
        top_level = get_record(self.root, "000001:test.ESP")
        self.assertEqual(top_level["source"], "Quests/TestQuest.json")
        self.assertEqual(top_level["path"], [])
        self.assertEqual(top_level["record"]["EditorID"], "TestQuest")

        embedded = get_record(self.root, "000002:Test.esp")
        self.assertEqual(embedded["source"], "Cells/0/0/TestCell/RecordData.json")
        self.assertEqual(embedded["path"], ["Persistent", 0])
        self.assertEqual(embedded["record"]["EditorID"], "TestReference")

    def test_gets_batch_in_input_order_with_one_tree_traversal(self) -> None:
        original_records = get_record_module.SpriggitTree.records
        traversal_count = 0

        def counted_records(tree):
            nonlocal traversal_count
            traversal_count += 1
            yield from original_records(tree)

        with patch.object(
            get_record_module.SpriggitTree,
            "records",
            counted_records,
        ):
            results = get_records(
                self.root,
                ["000002:Test.esp", "000001:test.ESP"],
            )

        self.assertEqual(traversal_count, 1)
        self.assertEqual(
            [result["record"]["FormKey"] for result in results],
            ["000002:Test.esp", "000001:Test.esp"],
        )

    def test_parses_batch_input_and_rejects_empty_or_duplicate_lines(self) -> None:
        self.assertEqual(
            parse_form_key_lines(
                ["\ufeff000002:Test.esp\n", "000001:test.ESP\n"]
            ),
            ["000002:Test.esp", "000001:test.ESP"],
        )
        with self.assertRaisesRegex(RecordLookupError, "empty FormKey.*line 2"):
            parse_form_key_lines(["000001:Test.esp\n", "\n"])
        with self.assertRaisesRegex(
            RecordLookupError,
            "duplicate FormKey.*line 2.*first supplied on line 1",
        ):
            parse_form_key_lines(
                ["000001:Test.esp\n", "000001:test.ESP\n"]
            )
        with self.assertRaisesRegex(RecordLookupError, "contains no entries"):
            parse_form_key_lines([])

    def test_batch_cli_writes_ordered_jsonl_and_fails_atomically(self) -> None:
        input_path = Path(self.temporary.name) / "formkeys.txt"
        input_path.write_text(
            "000002:Test.esp\n000001:Test.esp\n",
            encoding="utf-8",
        )
        output = io.StringIO()
        errors = io.StringIO()
        with patch.object(
            sys,
            "argv",
            [
                "get_record.py",
                str(self.root),
                "--formkeys-from",
                str(input_path),
            ],
        ), redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(get_record_module.main(), 0)

        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(
            [row["record"]["FormKey"] for row in rows],
            ["000002:Test.esp", "000001:Test.esp"],
        )

        input_path.write_text(
            "000001:Test.esp\nFFFFFF:Test.esp\n",
            encoding="utf-8",
        )
        output = io.StringIO()
        errors = io.StringIO()
        with patch.object(
            sys,
            "argv",
            [
                "get_record.py",
                str(self.root),
                "--formkeys-from",
                str(input_path),
            ],
        ), redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as raised:
                get_record_module.main()

        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("record not found: FFFFFF:Test.esp", errors.getvalue())

    def test_batch_cli_reads_standard_input(self) -> None:
        output = io.StringIO()
        errors = io.StringIO()
        standard_input = io.StringIO(
            "000001:Test.esp\n000002:Test.esp\n"
        )
        with patch.object(
            sys,
            "argv",
            [
                "get_record.py",
                str(self.root),
                "--formkeys-from",
                "-",
            ],
        ), patch.object(sys, "stdin", standard_input), redirect_stdout(
            output
        ), redirect_stderr(errors):
            self.assertEqual(get_record_module.main(), 0)

        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(
            [row["record"]["FormKey"] for row in rows],
            ["000001:Test.esp", "000002:Test.esp"],
        )

    def test_rejects_invalid_or_missing_form_keys(self) -> None:
        with self.assertRaisesRegex(RecordLookupError, "invalid FormKey"):
            get_record(self.root, "TestQuest")
        with self.assertRaisesRegex(RecordLookupError, "record not found"):
            get_record(self.root, "FFFFFF:Test.esp")

    def test_rejects_duplicate_requests_and_duplicate_records(self) -> None:
        with self.assertRaisesRegex(
            RecordLookupError,
            "duplicate requested FormKey at position 2",
        ):
            get_records(
                self.root,
                ["000001:Test.esp", "000001:test.ESP"],
            )

        self.write_json(
            "Quests/Duplicate.json",
            {
                "FormKey": "000001:Test.esp",
                "EditorID": "Duplicate",
            },
        )
        with self.assertRaisesRegex(RecordLookupError, "multiple records found"):
            get_record(self.root, "000001:Test.esp")


if __name__ == "__main__":
    unittest.main()
