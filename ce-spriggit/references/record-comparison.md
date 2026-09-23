# Record Comparison

This reference covers structural comparison of override definitions that share a FormKey.
It does not assign compatibility or author intent.

## Method

Select the definitions that answer the comparison question.

| Question | Definitions |
| --- | --- |
| Change introduced by a plugin | Latest definition from its declared masters and the plugin definition. |
| Effective load-order transition | Previous active definition and the plugin definition. |
| Final load-order state | Active winner. |
| Patch carry-forward | The source definition, its baseline, and the active winner. |

The declared-master definition and previous active definition can differ when unrelated plugins intervene.

Create an exact recursive diff.
Use the game's xEdit definitions for field-specific comparison rules.
Retain or explain every raw change in the final result.

## Representation traps

- Spriggit's translation package defines the text schema.
  Compare trees serialized with the same package name and version.
- A normal plugin definition contains a complete record payload, not a delta.
  A Partial Form definition is the exception.
- xEdit ignores a missing field marked as partial during conflict comparison.
  Treat this omission differently from a deletion.
- Some omitted values are implicit defaults, not deletions.
  Stage `0` can omit `Index`, and alias `0` can omit `ID`.
- xEdit can equate a missing optional field with present all-zero content.
  This rule applies only to supported scalar, struct, and array fields.
- `CELL` and `WRLD` JSON can embed child major records.
  References, landscapes, navigation meshes, and cells still override by their own FormKeys.
- Dialogue responses are nested below dialogue topics on disk.
  Each response still has an independent FormKey.
- `MajorRecordFlagsRaw`, the game-specific `*MajorRecordFlags`, and `MajorFlags` can expose the same header bits.
  `IsCompressed` exposes the compression bit again.
- A raw Spriggit diff includes fields that xEdit marks `cpIgnore`, including some format and version fields.

## Collection semantics

xEdit's `S` array constructors declare sorted arrays.
Display alignment does not make an unsorted array order-independent.

For an array that is not listed, preserve order and duplicate occurrences unless its xEdit definition declares it sorted.

### Skyrim fields

| Field | Comparison rule |
| --- | --- |
| `CELL.Regions` | Sorted. Align by FormKey and preserve duplicate occurrences. |
| VMAD scripts and properties | Sorted by name. Match duplicate names by occurrence. Property-value arrays remain ordered. |
| `QUST.Stages` and `QUST.Objectives` | Sorted by index. Duplicate indices remain separate occurrences. |
| `QUST.Aliases` | Unsorted. Alias ID is a correspondence key, but reordering remains a factual change. |
| Conditions | Unsorted and order-sensitive. An OR flag joins its condition to the next condition. Consecutive OR flags form an order-dependent block. A final OR affects later appended conditions. |
| `NPC_.Packages` | Unsorted. Stored order is meaningful. |
| Leveled-list entries | Sorted, but multiplicity remains significant. Identical duplicate entries change selection weight. |
