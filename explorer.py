#!/usr/bin/env python3
"""
RISC-V Instruction Set Explorer
================================
Coding Challenge Submission — RISC-V Mentorship Program 2026
Author : Eman Nasar | UET Lahore
GitHub : github.com/EmanNasar001/riscv-isa-explorer

Tiers implemented:
  Tier 1 — Parse instr_dict.json, group by extension, print summary table
  Tier 2 — Cross-reference extensions against RISC-V ISA manual AsciiDoc sources
  Tier 3 — Text-based sharing graph + unit tests

Design Decisions:
  - Extension name normalization strips 'rv_' / 'rv' prefixes and lowercases
    everything so that 'rv_zba', 'Zba', and 'ZBA' all compare equal.
  - The ISA manual regex is intentionally strict (min 3 chars, known prefixes)
    to avoid matching common English words that appear in prose sections.
  - Instructions are stored uppercase for consistent comparison.
  - Tier 2 scans all .adoc files recursively so future manual reorganizations
    are handled automatically.
"""

import json
import os
import re
import sys
import unittest
from pathlib import Path
from collections import defaultdict

# ─── PATHS ────────────────────────────────────────────────────────────────────
# These point to the two cloned repositories. Adjust if cloned elsewhere.
HOME            = Path.home()
INSTR_JSON      = HOME / "riscv-extensions-landscape" / "src" / "instr_dict.json"
ISA_MANUAL_SRC  = HOME / "riscv-isa-manual" / "src"


# ══════════════════════════════════════════════════════════════════════════════
#  TIER 1 — INSTRUCTION SET PARSING
# ══════════════════════════════════════════════════════════════════════════════

def load_instructions(json_path):
    """
    Load the instruction dictionary JSON file.

    The file contains one entry per instruction mnemonic. Each entry is a dict
    that may have an 'extension' or 'tags' key listing which ISA extensions
    define that instruction.

    Returns: dict  { mnemonic_string -> metadata_dict }
    """
    with open(json_path, "r") as f:
        return json.load(f)


def group_by_extension(instructions):
    """
    Group instruction mnemonics by their extension tag(s).

    Edge cases handled:
      - 'extension' value may be a list OR a bare string → normalised to list
      - 'tags' key used as fallback if 'extension' is absent
      - Instructions with no recognisable tag are silently skipped
        (avoids crashing on malformed entries)
      - Mnemonics stored in UPPER CASE for consistent display

    Returns:
      ext_map : dict  { extension_tag -> [mnemonic, ...] }
      multi   : list  [ (mnemonic, [tag, tag, ...]) ]  — shared instructions
    """
    ext_map = defaultdict(list)
    multi   = []

    for mnemonic, data in instructions.items():
        tags = []

        if isinstance(data, dict):
            # Prefer 'extension' key; fall back to 'tags'
            if "extension" in data:
                raw = data["extension"]
                tags = raw if isinstance(raw, list) else [raw]
            elif "tags" in data:
                raw = data["tags"]
                tags = raw if isinstance(raw, list) else [raw]
            # If neither key exists, tags stays [] and instruction is skipped

        for tag in tags:
            ext_map[tag].append(mnemonic.upper())

        # Track instructions that appear in more than one extension
        if len(tags) > 1:
            multi.append((mnemonic.upper(), tags))

    return dict(ext_map), multi


def print_tier1(ext_map, multi):
    """
    Print Tier 1 summary:
      • Table of extension | instruction count | example mnemonic
      • List of instructions shared across multiple extensions
    """
    print("\n" + "=" * 65)
    print(" TIER 1 — Instruction Set Summary by Extension")
    print("=" * 65)
    print(f"{'Extension':<25} {'Count':>7}  {'Example'}")
    print("-" * 65)

    for ext in sorted(ext_map.keys()):
        mnemonics = ext_map[ext]
        example   = mnemonics[0] if mnemonics else "N/A"
        print(f"{ext:<25} {len(mnemonics):>7}  e.g. {example}")

    print("-" * 65)
    total_instr = sum(len(v) for v in ext_map.values())
    print(f"Total extensions : {len(ext_map)}")
    print(f"Total instruction entries (with duplicates) : {total_instr}")

    print(f"\n--- Instructions belonging to MORE than one extension "
          f"({len(multi)}) ---")
    if multi:
        for mnemonic, tags in multi:
            print(f"  {mnemonic}: {', '.join(tags)}")
    else:
        print("  None found.")


# ══════════════════════════════════════════════════════════════════════════════
#  TIER 2 — CROSS-REFERENCE WITH ISA MANUAL
# ══════════════════════════════════════════════════════════════════════════════

def normalize(name):
    """
    Normalize an extension name for case-insensitive, prefix-insensitive
    comparison.

    Examples:
      'rv_zba'  -> 'zba'
      'Zba'     -> 'zba'
      'rv_m'    -> 'm'
      'RV32I'   -> '32i'

    Design decision: stripping the 'rv_' / 'rv' prefix is the minimal
    transformation that aligns JSON tags with ISA manual identifiers.
    Lowercasing handles the remaining case differences.
    """
    name = name.lower()
    name = re.sub(r'^rv_', '', name)   # remove 'rv_' prefix (JSON style)
    name = re.sub(r'^rv',  '', name)   # remove bare 'rv' prefix
    name = name.strip('_')
    return name


def get_json_extensions(ext_map):
    """
    Build a mapping of  { normalized_name -> original_name }
    for all extensions found in the JSON file.
    """
    return {normalize(e): e for e in ext_map.keys()}


def scan_manual_extensions(src_path):
    """
    Scan all AsciiDoc (.adoc) files under src_path for RISC-V extension names.

    Regex design decisions:
      - RV(32|64)?[IMAFDQCBVNH]+  matches base ISA strings like RV32I, RV64GC
      - Z[a-z]{2,}                matches Z-extensions like Zba, Zicsr (min 3
                                  chars avoids single-letter false positives)
      - Ss[a-z]{2,}               matches supervisor extensions like Ssaia
      - Sm[a-z]{2,}               matches machine extensions like Smaia
      - Case-sensitive: the ISA manual uses consistent capitalisation

    Known limitation: very short base extension letters (I, M, A, F, D, Q, C)
    are too common as English words to match reliably in prose — they are
    intentionally excluded from the single-letter match to avoid noise.

    Returns: dict  { normalized_name -> first_seen_original }
    """
    pattern = re.compile(
        r'\b('
        r'RV(?:32|64)?[IMAFDQCBVNH]+(?:[a-z][a-z0-9]*)?'  # RV32I, RV64GC …
        r'|Z[a-z]{2,}[a-z0-9_]*'                            # Zba, Zicsr …
        r'|Ss[a-z]{2,}'                                      # Ssaia, Sstc …
        r'|Sm[a-z]{2,}'                                      # Smaia …
        r')\b'
    )

    found      = {}
    adoc_files = list(Path(src_path).rglob("*.adoc"))

    print(f"\n[INFO] Scanning {len(adoc_files)} AsciiDoc files in ISA manual...")

    for filepath in adoc_files:
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
            for match in pattern.findall(text):
                norm = normalize(match)
                if norm not in found:
                    found[norm] = match   # keep first occurrence as canonical
        except Exception as e:
            # Non-fatal: log and continue scanning remaining files
            print(f"  [WARN] Could not read {filepath.name}: {e}")

    return found


def print_tier2(ext_map, src_path):
    """
    Print Tier 2 cross-reference report comparing:
      • Extensions in instr_dict.json
      • Extension identifiers found in RISC-V ISA manual AsciiDoc sources
    """
    print("\n" + "=" * 65)
    print(" TIER 2 — Cross-Reference: JSON vs ISA Manual")
    print("=" * 65)

    json_exts   = get_json_extensions(ext_map)
    manual_exts = scan_manual_extensions(src_path)

    json_keys   = set(json_exts.keys())
    manual_keys = set(manual_exts.keys())

    matched     = json_keys & manual_keys          # intersection
    json_only   = json_keys  - manual_keys         # in JSON, not manual
    manual_only = manual_keys - json_keys          # in manual, not JSON

    # ── Summary counts ──────────────────────────────────────────────────────
    print(f"\n  Matched (in both)      : {len(matched)}")
    print(f"  JSON only              : {len(json_only)}")
    print(f"  ISA manual only        : {len(manual_only)}")

    # ── Detail lists ────────────────────────────────────────────────────────
    print(f"\n--- In JSON but NOT in ISA manual ({len(json_only)}) ---")
    for n in sorted(json_only):
        print(f"  {json_exts[n]}")

    print(f"\n--- In ISA manual but NOT in JSON ({len(manual_only)}) ---")
    for n in sorted(manual_only):
        print(f"  {manual_exts[n]}")

    print(f"\n--- Matched ({len(matched)}) ---")
    for n in sorted(matched):
        print(f"  {json_exts[n]:<25} <->  {manual_exts[n]}")

    print(f"\nSummary: {len(matched)} matched, "
          f"{len(json_only)} in JSON only, "
          f"{len(manual_only)} in manual only")


# ══════════════════════════════════════════════════════════════════════════════
#  TIER 3 — SHARING GRAPH
# ══════════════════════════════════════════════════════════════════════════════

def print_graph(ext_map):
    """
    Print a text-based adjacency graph of extensions that share instructions.

    Algorithm:
      1. Build reverse map: instruction -> list of extensions that define it
      2. Any instruction with 2+ extensions creates an edge between each pair
      3. Edges stored in a set to avoid duplicates
      4. Output each node with its sorted neighbour list

    This is an undirected graph — if A shares with B, B also shows A.
    """
    print("\n" + "=" * 65)
    print(" TIER 3 — Extension Sharing Graph (text-based adjacency list)")
    print("=" * 65)
    print("\n  Two extensions are connected if they share ≥1 instruction.")
    print("  Format:  Extension  -->  [connected extensions]\n")

    # Step 1: reverse map — instruction -> extensions
    instr_to_exts = defaultdict(list)
    for ext, mnemonics in ext_map.items():
        for m in mnemonics:
            instr_to_exts[m].append(ext)

    # Step 2: build adjacency sets
    adjacency = defaultdict(set)
    for m, exts in instr_to_exts.items():
        if len(exts) > 1:
            # Add edge between every pair of extensions sharing this instruction
            for i in range(len(exts)):
                for j in range(i + 1, len(exts)):
                    adjacency[exts[i]].add(exts[j])
                    adjacency[exts[j]].add(exts[i])

    if not adjacency:
        print("  No extensions share instructions.")
        return

    # Step 3: print sorted adjacency list
    for ext in sorted(adjacency.keys()):
        neighbours = ", ".join(sorted(adjacency[ext]))
        print(f"  {ext:<25} --> {neighbours}")


# ══════════════════════════════════════════════════════════════════════════════
#  TIER 3 — UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestExplorer(unittest.TestCase):
    """Unit tests for parsing, grouping, normalization, and cross-reference."""

    def test_normalize_rv_prefix(self):
        """rv_ prefix should be stripped."""
        self.assertEqual(normalize("rv_zba"), "zba")
        self.assertEqual(normalize("rv_m"),   "m")

    def test_normalize_capital(self):
        """Capital Z-extensions should normalize to lowercase."""
        self.assertEqual(normalize("Zba"),   "zba")
        self.assertEqual(normalize("Zicsr"), "zicsr")

    def test_normalize_rv32(self):
        """RV32/RV64 prefixes should be handled."""
        self.assertEqual(normalize("RV32I"), "32i")

    def test_group_single_extension(self):
        """Instruction in one extension should not appear in multi list."""
        fake = {"add": {"extension": ["rv_i"]}}
        ext_map, multi = group_by_extension(fake)
        self.assertIn("rv_i", ext_map)
        self.assertIn("ADD", ext_map["rv_i"])
        self.assertEqual(multi, [])

    def test_group_multiple_extensions(self):
        """Instruction in two extensions should appear in multi list."""
        fake = {"fadd.s": {"extension": ["rv_f", "rv_zfinx"]}}
        ext_map, multi = group_by_extension(fake)
        self.assertEqual(len(multi), 1)
        self.assertEqual(multi[0][0], "FADD.S")
        self.assertIn("rv_f",    ext_map)
        self.assertIn("rv_zfinx", ext_map)

    def test_group_empty(self):
        """Empty input should produce empty outputs."""
        ext_map, multi = group_by_extension({})
        self.assertEqual(ext_map, {})
        self.assertEqual(multi,   [])

    def test_group_missing_extension_key(self):
        """Instructions with no extension key should be skipped gracefully."""
        fake = {"nop": {"description": "no operation"}}
        ext_map, multi = group_by_extension(fake)
        self.assertEqual(ext_map, {})

    def test_normalize_idempotent(self):
        """Normalizing an already-normalized name should be stable."""
        self.assertEqual(normalize(normalize("rv_zba")), normalize("rv_zba"))


def run_tests():
    """Run all unit tests and print results."""
    print("\n" + "=" * 65)
    print(" TIER 3 — Unit Tests")
    print("=" * 65)
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromTestCase(TestExplorer)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 65)
    print(" RISC-V Instruction Set Explorer")
    print(" Eman Nasar | UET Lahore | 2026")
    print("=" * 65)

    # ── Validate required paths ──────────────────────────────────────────────
    if not INSTR_JSON.exists():
        print(f"[ERROR] Cannot find: {INSTR_JSON}")
        print("        Clone: https://github.com/rpsene/riscv-extensions-landscape")
        sys.exit(1)

    if not ISA_MANUAL_SRC.exists():
        print(f"[ERROR] Cannot find: {ISA_MANUAL_SRC}")
        print("        Clone: https://github.com/riscv/riscv-isa-manual")
        sys.exit(1)

    # ── Load data ────────────────────────────────────────────────────────────
    print(f"\n[INFO] Loading {INSTR_JSON.name} ...")
    instructions = load_instructions(INSTR_JSON)
    print(f"[INFO] {len(instructions)} instructions loaded.")

    # ── Run all tiers ────────────────────────────────────────────────────────
    ext_map, multi = group_by_extension(instructions)

    print_tier1(ext_map, multi)
    print_tier2(ext_map, ISA_MANUAL_SRC)
    print_graph(ext_map)
    run_tests()


if __name__ == "__main__":
    main()
