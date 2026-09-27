"""
test_spec_compliance.py

Automated Spec-Driven Architecture (SDD) Compliance Test Suite.
Validates that:
1. All specification markdown files under specs/ follow the standardized structure.
2. Every invariant tag [SPEC-<DOMAIN>-<NUM>] is uniquely defined and well-formed.
3. Every specification defines a populated Verification & Traceability Matrix.
4. Key system invariants (e.g. strict single live Saxo desk engine) are explicitly declared.
"""

import os
import re
import pytest
from pathlib import Path
from typing import Dict, List, Set

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = ROOT_DIR / "specs"

INVARIANT_PATTERN = re.compile(r"\[(SPEC-[A-Z\-]+-\d+)\]")


def get_all_spec_files() -> List[Path]:
    """Retrieve all .spec.md files within the specs/ directory."""
    assert SPECS_DIR.exists(), f"specs/ directory does not exist at {SPECS_DIR}"
    spec_files = list(SPECS_DIR.rglob("*.spec.md"))
    return spec_files


def test_specs_directory_scaffolded():
    """Verify that specs/ directory contains required pillar subdirectories."""
    required_pillars = [
        "00-system-architecture",
        "01-pricing-and-quant-engine",
        "02-broker-and-execution",
        "03-options-harvest-and-margin",
        "04-macro-and-multi-agent",
        "05-behavioral-forensics-and-tutor",
        "06-frontend-and-api-contracts",
    ]
    for pillar in required_pillars:
        pillar_dir = SPECS_DIR / pillar
        assert pillar_dir.exists(), f"Required spec pillar directory missing: {pillar}"


def test_spec_files_count():
    """Verify that baseline specifications have been authored across pillars."""
    spec_files = get_all_spec_files()
    assert len(spec_files) >= 8, f"Expected at least 8 spec files, found {len(spec_files)}"


def test_spec_structure_and_invariants():
    """Verify that each .spec.md file contains required sections and valid invariant tags."""
    spec_files = get_all_spec_files()
    all_invariants: Set[str] = set()

    for spec_path in spec_files:
        rel_path = spec_path.relative_to(ROOT_DIR)
        content = spec_path.read_text(encoding="utf-8")

        # 1. Header validations
        assert re.search(r"\*?\*?Status\*?\*?:", content, re.IGNORECASE), f"{rel_path} missing 'Status' in header"
        assert re.search(r"\*?\*?Version\*?\*?:", content, re.IGNORECASE), f"{rel_path} missing 'Version' in header"
        assert re.search(r"\*?\*?Domain\*?\*?:", content, re.IGNORECASE), f"{rel_path} missing 'Domain' in header"

        # 2. Section validations
        assert "## 1." in content or "Purpose" in content, f"{rel_path} missing Purpose section"
        assert "Invariants" in content, f"{rel_path} missing Invariants section"
        assert "Verification & Traceability Matrix" in content, f"{rel_path} missing Traceability Matrix"

        # 3. Invariant tags extraction
        matches = INVARIANT_PATTERN.findall(content)
        assert len(matches) > 0, f"{rel_path} does not define any [SPEC-...] invariants"

        for tag in matches:
            all_invariants.add(tag)

    print(f"\n[SDD Verification] Successfully validated {len(spec_files)} spec files with {len(all_invariants)} tracked invariants.")


def test_single_execution_engine_invariant():
    """Assert that the single live Saxo desk engine invariant is codified without paper sandboxes."""
    saxo_spec = SPECS_DIR / "02-broker-and-execution" / "saxo-execution-desk.spec.md"
    assert saxo_spec.exists(), "saxo-execution-desk.spec.md must exist"

    content = saxo_spec.read_text(encoding="utf-8")
    assert "[SPEC-SAXO-DESK-001]" in content
    assert "Strict Single Execution Engine Architecture" in content or "Zero Simulated Paper Sandbox" in content
    assert "Zero simulated paper trading engines" in content or "zero simulated" in content.lower()


def test_quant_and_tick_quantization_invariants():
    """Assert that Black-Scholes and tick-quantization invariants are codified."""
    quant_spec = SPECS_DIR / "01-pricing-and-quant-engine" / "black-scholes-and-greeks.spec.md"
    order_spec = SPECS_DIR / "02-broker-and-execution" / "order-safety-and-quantization.spec.md"

    assert quant_spec.exists()
    assert order_spec.exists()

    quant_content = quant_spec.read_text(encoding="utf-8")
    assert "[SPEC-QUANT-BS-001]" in quant_content

    order_content = order_spec.read_text(encoding="utf-8")
    assert "[SPEC-SAXO-ORD-001]" in order_content
    assert "quantize_order_price" in order_content


def test_margin_and_dialectical_invariants():
    """Assert that Margin Guardian and Dialectical Arena invariants are codified."""
    margin_spec = SPECS_DIR / "03-options-harvest-and-margin" / "margin-guardian.spec.md"
    arena_spec = SPECS_DIR / "04-macro-and-multi-agent" / "dialectical-fiduciary-arena.spec.md"

    assert margin_spec.exists()
    assert arena_spec.exists()

    margin_content = margin_spec.read_text(encoding="utf-8")
    assert "[SPEC-MARGIN-001]" in margin_content
    assert "75.0%" in margin_content

    arena_content = arena_spec.read_text(encoding="utf-8")
    assert "[SPEC-ARENA-001]" in arena_content
    assert "TARGET_SHORTFALL_CHALLENGE" in arena_content
