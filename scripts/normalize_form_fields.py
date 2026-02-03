#!/usr/bin/env python3
"""
Normalize form fields to the canonical schema used by the backend and frontend.

Canonical field shape (backend + frontend):
  - label (string, required)
  - apiName (string | null)
  - type ("text" | "picklist" | "radio" | "number" | "textarea")
  - required (boolean)
  - possibleValues (string[])
  - defaultValue (string | null)

Optional frontend-only key (ignored by backend): formGroup (string)

Usage:
  python scripts/normalize_form_fields.py test-data/fields/001XX000001_fields.json
  python scripts/normalize_form_fields.py --add-form-groups test-data/fields/001XX000001_fields.json

Reads JSON with root {"fields": [...]}, normalizes each field, optionally assigns
formGroup by splitting across the five default groups, and writes back.
"""

import argparse
import json
import sys
from pathlib import Path

# Default form group names in display order (five pages)
DEFAULT_FORM_GROUP_ORDER = [
    "Véhicle et passagers adverses",
    "Passagers assurés",
    "Véhicles assurés",
    "Infos des circonstances",
    "Infos dommages autres parties",
]

VALID_TYPES = {"text", "picklist", "radio", "number", "textarea"}


def normalize_field(raw: dict, form_group: str | None = None) -> dict:
    """Build a canonical field object from a raw field dict."""
    label = (raw.get("label") or raw.get("ariaLabel") or "").strip() or "Sans libellé"
    api_name = raw.get("apiName") or raw.get("dataOmniKey") or None
    raw_type = (raw.get("type") or "text").lower()
    if raw_type not in VALID_TYPES:
        raw_type = "text"
    required = bool(raw.get("required", False))
    possible_values = list(raw.get("possibleValues") or raw.get("options") or [])
    default_value = raw.get("defaultValue") or raw.get("value") or None

    out = {
        "label": label,
        "apiName": api_name,
        "type": raw_type,
        "required": required,
        "possibleValues": possible_values,
        "defaultValue": default_value,
    }
    if form_group is not None:
        out["formGroup"] = form_group
    return out


def add_form_groups(fields: list[dict], group_order: list[str]) -> list[dict]:
    """Assign formGroup to each field by splitting across group_order."""
    n = len(group_order)
    chunk_size = (len(fields) + n - 1) // n if n else 0
    result = []
    for i, f in enumerate(fields):
        group_index = min(i // chunk_size, n - 1) if chunk_size else 0
        result.append(normalize_field(f, form_group=group_order[group_index]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize form fields JSON")
    parser.add_argument(
        "path",
        type=Path,
        help="Path to JSON file with root {\"fields\": [...]}",
    )
    parser.add_argument(
        "--add-form-groups",
        action="store_true",
        help="Assign formGroup to each field by splitting across the five default groups",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: overwrite input)",
    )
    args = parser.parse_args()

    path = args.path
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    fields = data.get("fields", [])
    if not isinstance(fields, list):
        print("Error: 'fields' must be an array", file=sys.stderr)
        return 1

    if args.add_form_groups:
        normalized = add_form_groups(fields, DEFAULT_FORM_GROUP_ORDER)
    else:
        normalized = [normalize_field(f) for f in fields]

    out_data = {"fields": normalized}
    out_path = args.out or path
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(normalized)} fields to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
