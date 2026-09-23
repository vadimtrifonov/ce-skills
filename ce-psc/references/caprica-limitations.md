# Caprica Limitations

The helper uses [KrisV-777/Caprica 0.3.0a](https://github.com/KrisV-777/Caprica/releases/tag/0.3.0a) in Skyrim mode without Caprica language extensions or forced optimization.

## Preflight rules

### Source encoding

Caprica rejects a PSC that starts with a UTF-8 byte-order mark (BOM).
The compile helper therefore requires UTF-8 without a BOM.

Upstream issue: [Orvid/Caprica#37](https://github.com/Orvid/Caprica/issues/37)

### Leading-zero integers

Caprica parses decimal integers with a leading zero as octal values.
The error changes generated program data without a compiler failure.

```papyrus
08   ; PEX value: 0
0124 ; PEX value: 84
```

The compile helper rejects all leading-zero decimal integer tokens outside comments and strings.
Hexadecimal literals such as `0x0008` remain valid.

Upstream issue: [Orvid/Caprica#31](https://github.com/Orvid/Caprica/issues/31)

### Duplicate functions and events

Caprica can return success for duplicate function declarations and keep only the first body.
The compile helper rejects duplicate function or event names within one state.
The same name in different states remains valid.

Related upstream issue: [Orvid/Caprica#33](https://github.com/Orvid/Caprica/issues/33)

## Compiler behavior

### Compound assignment to array elements

Caprica evaluates an array index expression twice for a compound assignment.
For example, `values[GetIndex()] += 1` calls `GetIndex()` two times.
Store an index with side effects in a variable before the compound assignment.

Upstream issue: [Orvid/Caprica#11](https://github.com/Orvid/Caprica/issues/11)

### String ordering

Bethesda's compiler accepts relational comparisons between strings.
Caprica rejects string operands for `<`, `<=`, `>`, and `>=`.
String equality and concatenation are supported.

Upstream issue: [Orvid/Caprica#13](https://github.com/Orvid/Caprica/issues/13)

### Deliberate compiler differences

Caprica documents differences from Bethesda's compiler for these language cases:

- Implicit conversion from `None` to `Bool`, `String`, arrays, and objects.
- Access to auto-property backing variables declared by parent scripts.

The details are in the Caprica [Deliberate Differences](https://github.com/KrisV-777/Caprica/blob/0.3.0a/README.md) section.
These cases can cause a compiler error or different property-access code.

## Output behavior

### PEX hash differences

Caprica writes the source path, user name, computer name, and compilation time into the PEX header.
Builds made at different times or from different source paths have different file hashes.
The `--anonymize` option has no effect.
The identifying values remain in the PEX.
