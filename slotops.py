# ==============================================================================
# Author       : John
# Description  : Core rules parsing/validation, code generation, semantic
#                diff, batch validation.
# ==============================================================================
from __future__ import annotations

import glob
import json
import logging
import os
import time

from rule_catalog import CATALOG

logger = logging.getLogger(__name__)

VALID_SEVERITIES = {"ERROR", "WARNING", "INFO"}
PRIORITY = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

RULES_FILE = "studio/rules.md"
TEMPLATE_FILE = "studio/templates/validator.py.template"
OUTPUT_DIR = "studio/generated"
OUTPUT_FILE = "studio/generated/validator.py"
CONFIG_TEMPLATE = "studio/config_template.json"
IMPORTANCE_FILE = "studio/field_importance.json"


# =========================================================================== #
# 1. RULES: parse & validate
# =========================================================================== #
def parse_rules_md(filepath: str) -> list[dict[str, str]]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    rules = []
    for block in content.split("## "):
        if not block.strip() or block.startswith("#"):
            continue
        lines = block.strip().split("\n")
        rule = {"id": lines[0].strip()}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                rule[k.strip().lower()] = v.strip()
        rules.append(rule)
    return rules


def _flatten_schema(schema: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for k, v in schema.items():
        full = f"{prefix}.{k}" if prefix else k
        keys.add(full)
        if isinstance(v, dict):
            keys.update(_flatten_schema(v, full))
    return keys


def _rule_errors(rule: dict, seen: set, valid_fields: set) -> list[str]:
    r_id = rule.get("id")
    errs = []
    if not r_id or r_id in seen:
        errs.append(f"[{r_id or 'UNKNOWN'}] Duplicate or missing Rule ID")
    if rule.get("severity") not in VALID_SEVERITIES:
        errs.append(f"[{r_id}] Invalid Severity: '{rule.get('severity')}' (ERROR|WARNING|INFO)")
    if rule.get("field") not in valid_fields:
        errs.append(f"[{r_id}] Field '{rule.get('field')}' not in config_template.json")
    if not rule.get("condition"):
        errs.append(f"[{r_id}] Missing condition statement")
    return errs


def validate_rules(rules_file: str = RULES_FILE, template_file: str = CONFIG_TEMPLATE) -> bool:
    logger.info("Validating rules: %s", rules_file)
    with open(template_file, "r", encoding="utf-8") as f:
        valid_fields = _flatten_schema(json.load(f))

    rules = parse_rules_md(rules_file)
    md_ids = {r.get("id") for r in rules}
    catalog_ids = set(CATALOG)

    has_errors = False
    seen: set = set()

    # --- Per-rule metadata checks ------------------------------------------ #
    for rule in rules:
        errs = _rule_errors(rule, seen, valid_fields)
        seen.add(rule.get("id"))
        if errs:
            has_errors = True
            for e in errs:
                logger.error("  ✗ %s", e)
        else:
            logger.info("  ✓ %-12s | %-15s | %s",
                        rule["id"], rule["field"], rule["severity"])

    # --- Bidirectional sync: rules.md <-> rule_catalog --------------------- #
    for r_id in sorted(md_ids - catalog_ids):
        has_errors = True
        logger.error("  ✗ [%s] in rules.md but MISSING in rule_catalog.py", r_id)
    for r_id in sorted(catalog_ids - md_ids):
        has_errors = True
        logger.error("  ✗ [%s] in rule_catalog.py but MISSING in rules.md (dead rule)", r_id)

    if has_errors:
        logger.error("Rule validation FAILED.")
        return False
    logger.info("All rules valid and in sync with catalog.")
    logger.info("Done!")
    return True


# =========================================================================== #
# 2. GENERATOR: rules.md -> validator.py
# =========================================================================== #
def _rule_to_code(rule: dict) -> str:
    r_id = rule["id"].replace("-", "_").lower()
    rule_def = CATALOG.get(rule["id"])
    if rule_def is None:
        raise RuntimeError(f"No code template for rule {rule['id']} (run validate_rules first)")
    return rule_def.render(
        r_id=r_id, field=rule["field"],
        severity=rule["severity"], rule_id=rule["id"],
    )


def generate_code() -> None:
    logger.info("Transpiling %s -> %s", RULES_FILE, OUTPUT_FILE)
    rules = parse_rules_md(RULES_FILE)
    funcs = [_rule_to_code(r) for r in rules]
    names = [f"    validate_{r['id'].replace('-', '_').lower()}," for r in rules]

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    final = (
        template
        .replace("{{ GENERATED_RULE_FUNCTIONS }}", "\n\n".join(funcs))
        .replace("{{ GENERATED_RULE_LIST }}", "\n".join(names))
    )
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final)
    logger.info("Generated %d rule function(s).", len(rules))
    logger.info("Done!")


# =========================================================================== #
# 3. COMPARE: semantic diff V1 vs V2
# =========================================================================== #
class ConfigComparer:
    def __init__(self, importance_file: str = IMPORTANCE_FILE):
        with open(importance_file, "r", encoding="utf-8") as f:
            self.importance_map: dict[str, str] = json.load(f)

    def _importance(self, field_path: str) -> str:
        if field_path in self.importance_map:
            return self.importance_map[field_path]
        return self.importance_map.get(field_path.split(".")[0], "LOW")

    def _make(self, field: str, old, new, impact: str) -> dict:
        return {"field": field, "old": str(old), "new": str(new),
                "importance": self._importance(field), "impact": impact}

    def compare(self, old: dict, new: dict, path: str = "") -> list[dict]:
        diffs = []
        for key in set(old) | set(new):
            cur = f"{path}.{key}" if path else key
            o, n = old.get(key), new.get(key)
            if key not in old:
                diffs.append(self._make(cur, "N/A", n, "Added"))
            elif key not in new:
                diffs.append(self._make(cur, o, "N/A", "Removed"))
            elif isinstance(o, dict) and isinstance(n, dict):
                diffs.extend(self.compare(o, n, cur))
            elif o != n:
                imp = self._importance(cur)
                impact = {"HIGH": "Significant change", "MEDIUM": "Changed"}.get(imp, "Minor change")
                diffs.append(self._make(cur, o, n, impact))
        return diffs


def print_comparison_report(file1: str, file2: str) -> None:
    logger.info("Comparing configs: %s vs %s", file1, file2)
    with open(file1, "r", encoding="utf-8") as f1, open(file2, "r", encoding="utf-8") as f2:
        c1, c2 = json.load(f1), json.load(f2)

    diffs = ConfigComparer().compare(c1, c2)
    diffs.sort(key=lambda d: PRIORITY.get(d["importance"], 3))

    logger.info("Found %d difference(s).", len(diffs))
    for d in diffs:
        logger.info("%-20s %-25s %-12s %s",
                    d["field"], f"{d['old']} -> {d['new']}", d["importance"], d["impact"])
    logger.info("Done!")


# =========================================================================== #
# 4. BATCH run validator over a directory
# =========================================================================== #
def run_batch_validation(config_dir: str) -> dict:
    from studio.generated.validator import validate

    logger.info("Batch validation: %s", config_dir)
    files = glob.glob(os.path.join(config_dir, "**", "*.json"), recursive=True)
    stats = {"total": len(files), "valid": 0, "errors": 0, "warnings": 0}
    start = time.time()

    for filepath in files:
        rel = os.path.relpath(filepath, config_dir)
        with open(filepath, "r", encoding="utf-8") as f:
            issues = validate(json.load(f))

        if not issues:
            status, stats["valid"] = "PASS", stats["valid"] + 1
        elif any(i["severity"] == "ERROR" for i in issues):
            status, stats["errors"] = "FAIL", stats["errors"] + 1
        else:
            status, stats["warnings"] = "WARN", stats["warnings"] + 1

        logger.info("[%-4s] %s", status, rel)
        for i in issues:
            logger.warning("  ↳ %s | %s (%s): %s",
                           i["severity"], i["rule_id"], i["field"], i["message"])

    stats["elapsed"] = time.time() - start
    logger.info(
        "Summary: %d total | %d valid | %d errors | %d warnings | %.2fs",
        stats["total"], stats["valid"], stats["errors"], stats["warnings"], stats["elapsed"],
    )
    logger.info("Done!")
    return stats


def validate_file(filepath: str) -> list[dict]:
    """
    Validate a single config file against the generated validator.

    Returns the list of issues (empty = PASS).
    Raises FileNotFoundError if the file does not exist,
    and json.JSONDecodeError if the file is not valid JSON.
    """
    from studio.generated.validator import validate

    logger.info("Validating file: %s", filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        issues = validate(json.load(f))

    if not issues:
        logger.info("  ✓ PASS")
    else:
        for i in issues:
            logger.warning("  ↳ %s | %s (%s): %s",
                           i["severity"], i["rule_id"], i["field"], i["message"])
    return issues
