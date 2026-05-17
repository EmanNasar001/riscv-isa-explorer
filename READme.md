# RISC-V Instruction Set Explorer

Coding challenge submission for the **RISC-V Mentorship Program 2026**

**Author:** Eman Nasar | UET Lahore
**GitHub:** [github.com/EmanNasar001/riscv-isa-explorer](https://github.com/EmanNasar001/riscv-isa-explorer)

---

## What This Does

A Python program that explores the RISC-V instruction set across three tiers:

| Tier | Description |
|------|-------------|
| **Tier 1** | Parses `instr_dict.json`, groups instructions by extension tag, prints summary table, identifies shared instructions |
| **Tier 2** | Scans RISC-V ISA manual AsciiDoc sources, cross-references extension names against JSON, reports matches and mismatches |
| **Tier 3** | Text-based sharing graph (extensions connected by shared instructions) + 8 unit tests |

---

## Prerequisites

- Python 3.8+
- Git

No third-party libraries required — uses only Python standard library.

---

## Setup and Run

### Step 1 — Clone the two data repositories

```bash
git clone --depth=1 https://github.com/rpsene/riscv-extensions-landscape
git clone --depth=1 https://github.com/riscv/riscv-isa-manual
```

### Step 2 — Clone this repository

```bash
git clone https://github.com/EmanNasar001/riscv-isa-explorer
cd riscv-isa-explorer
```

### Step 3 — Run

```bash
python3 explorer.py
```

All three tiers and unit tests run automatically.

---

## Sample Output

### Tier 1 — Extension Summary Table

```
=================================================================
 TIER 1 — Instruction Set Summary by Extension
=================================================================
Extension                   Count  Example
-----------------------------------------------------------------
rv32_c                          1  e.g. C_JAL
rv64_zba                        5  e.g. ADD_UW
rv_i                           37  e.g. ADD
rv_v                          627  e.g. VAADD_VV
rv_zba                          3  e.g. SH1ADD
-----------------------------------------------------------------
Total extensions : 114
Total instruction entries (with duplicates) : 1343
```

### Tier 2 — Cross-Reference Summary

```
[INFO] Scanning 158 AsciiDoc files in ISA manual...
  Matched (in both)      : 55
  JSON only              : 59
  ISA manual only        : 12
Summary: 55 matched, 59 in JSON only, 12 in manual only
```

### Tier 3 — Unit Tests

```
Ran 8 tests in 0.001s  OK
```

---

## Design Decisions

### Extension Name Normalization
The two sources use different naming conventions:

| Source | Format | Example |
|--------|--------|---------|
| `instr_dict.json` | lowercase with `rv_` prefix | `rv_zba`, `rv_m` |
| ISA manual | Mixed case, no prefix | `Zba`, `RV32I` |

Normalization strips `rv_` / `rv` prefix and lowercases so `rv_zba`, `Zba`, `ZBA` all compare as `zba`.

### ISA Manual Regex
Targets four known patterns only to avoid matching English prose words:
- `RV(32|64)?[IMAFDQCBVNH]+` — base ISA like `RV32I`, `RV64GC`
- `Z[a-z]{2,}` — Z-extensions like `Zba`, `Zicsr`
- `Ss[a-z]{2,}` — supervisor extensions like `Ssaia`
- `Sm[a-z]{2,}` — machine extensions like `Smaia`

### No Third-Party Libraries
Uses only Python standard library so reviewers can run immediately without pip install.

---

## Edge Cases Handled

| Edge Case | How Handled |
|-----------|-------------|
| `extension` value is string not list | Wrapped in list |
| Instruction has no extension key | Silently skipped |
| AsciiDoc file unreadable | Warning printed, scanning continues |
| Extension name casing differs | Normalization applied to both sides |
| Same instruction in 3+ extensions | Detected and listed |
| Empty instruction dictionary | Returns empty outputs gracefully |

---

## File Structure

```
riscv-isa-explorer/
├── explorer.py     # Main program (all tiers + tests)
└── README.md       # This file
```
