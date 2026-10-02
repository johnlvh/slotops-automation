# ==============================================================================
# Author       : John
# Description  : Rule catalog, every rule's code template lives here.
#                rules.md (Ops-editable) and this catalog MUST stay in sync;
#                validate_rules() enforces that bidirectionally.
#
#  ADD a rule    : add an entry below + a matching `## RULE-XXX` block in rules.md.
#  REMOVE a rule : delete both.
#  Orphan on either side => validation FAILS (by design).
# ==============================================================================
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleDef:
    render: Callable[..., str]


CATALOG: dict[str, RuleDef] = {
    "RULE-001": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    val = config.get("minBet")
    if val is not None and val <= 0:
        issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", f"minBet must be > 0. Found: {{val}}", "{k['severity']}"))
    return issues'''),

    "RULE-002": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    min_b = config.get("minBet")
    max_b = config.get("maxBet")
    if min_b is not None and max_b is not None and max_b <= min_b:
        issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", f"maxBet ({{max_b}}) must be > minBet ({{min_b}})", "{k['severity']}"))
    return issues'''),

    "RULE-003": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    jp_val = config.get("jackpot", {{}}).get("value")
    if jp_val is not None and jp_val > 1000000:
        issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", f"jackpot.value ({{jp_val}}) exceeds 1000000", "{k['severity']}"))
    return issues'''),

    "RULE-004": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    camp = config.get("campaign", {{}})
    start_str, end_str = camp.get("start"), camp.get("end")
    if start_str and end_str:
        try:
            start = datetime.fromisoformat(start_str)
            end = datetime.fromisoformat(end_str)
            if start >= end:
                issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", f"campaign.start must be earlier than campaign.end", "{k['severity']}"))
        except ValueError:
            issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", "Invalid ISO datetime for campaign start/end", "ERROR"))
    return issues'''),

    "RULE-005": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    active = config.get("campaign", {{}}).get("enabled", False)
    if not config.get("enabled", True) and active:
        issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", "Disabled game must not have an active campaign", "{k['severity']}"))
    return issues'''),

    "RULE-006": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    jp = config.get("jackpot", {{}})
    if not jp.get("enabled", False) and jp.get("value", 0) > 0:
        issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", f"jackpot.value must be 0 when disabled", "{k['severity']}"))
    return issues'''),

    "RULE-007": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    end_str = config.get("campaign", {{}}).get("end")
    if end_str:
        try:
            end = datetime.fromisoformat(end_str)
            now = datetime.now(timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if end <= now:
                issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", "campaign.end must be in the future", "{k['severity']}"))
        except ValueError:
            issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", "Invalid ISO datetime for campaign.end", "ERROR"))
    return issues'''),

    "RULE-008": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    gid = config.get("gameId")
    if gid is None or str(gid).strip() == "":
        issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", "gameId must not be empty", "{k['severity']}"))
    return issues'''),

    "RULE-009": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    APPROVED = {{"DOUBLE_XP", "FREE_SPINS", "JACKPOT_BOOST", "VIP_PASS", "SEASON_EVENT"}}
    for flag in config.get("featureFlags", []) or []:
        if flag not in APPROVED:
            issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", f"Unapproved feature flag: '{{flag}}'", "{k['severity']}"))
    return issues'''),

    "RULE-010": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
    issues = []
    seen, dups = set(), set()
    for item in config.get("rewards", []) or []:
        if isinstance(item, dict) and item.get("id"):
            rid = item["id"]
            (dups if rid in seen else seen).add(rid)
    for dup in dups:
        issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", f"Duplicate reward ID: '{{dup}}'", "{k['severity']}"))
    return issues'''),
}