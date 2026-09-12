"""Inspect Terraform JSON plans without emitting before/after values."""
TITLE = "Change Risk RAG"
DEFAULT_QUESTION = "Review Terraform deployment risk: deletion, replacement, public ingress, unknown values, rollback and staged rollout."
STATEFUL = {"aws_db_instance", "aws_rds_cluster", "aws_ebs_volume", "aws_s3_bucket",
            "google_sql_database_instance", "azurerm_postgresql_flexible_server"}
VALID = {("no-op",), ("create",), ("read",), ("update",), ("delete",),
         ("delete", "create"), ("create", "delete"), ("forget",), ("create", "forget")}

def truthy_unknown(value):
    if isinstance(value, dict):
        return any(truthy_unknown(v) for v in value.values())
    if isinstance(value, list):
        return any(truthy_unknown(v) for v in value)
    return value is True

def has_world_cidr(value):
    if isinstance(value, dict):
        return any(has_world_cidr(v) for v in value.values())
    if isinstance(value, list):
        return any(has_world_cidr(v) for v in value)
    return isinstance(value, str) and value in {"0.0.0.0/0", "::/0"}

def analyze(data):
    if not isinstance(data, dict) or not isinstance(data.get("resource_changes"), list):
        raise ValueError("Expected Terraform plan JSON with resource_changes")
    if str(data.get("format_version", "")).split(".")[0] != "1":
        raise ValueError("Only Terraform JSON format major version 1 is supported")
    findings, summaries = [], []
    def flag(code, severity, address, message):
        findings.append({"code": code, "severity": severity, "resource": address,
                         "message": address + ": " + message})
    if data.get("errored") is True:
        flag("ERRORED_PLAN", "critical", "plan", "Terraform planning failed; do not apply this plan.")
    if data.get("complete") is False:
        flag("INCOMPLETE_PLAN", "unknown", "plan", "Plan is incomplete; additional planning may be necessary.")
    for item in data["resource_changes"]:
        if not isinstance(item, dict) or not isinstance(item.get("address"), str):
            raise ValueError("Each resource change requires an address")
        change = item.get("change", {})
        actions = change.get("actions")
        if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
            raise ValueError("Change actions must be a string list")
        if tuple(actions) not in VALID:
            raise ValueError("Unsupported Terraform action sequence")
        address, kind = item["address"], item.get("type", "unknown")
        if actions in (["no-op"], ["read"]):
            continue
        summaries.append({"address": address, "type": kind, "actions": actions})
        if "delete" in actions:
            replace = "create" in actions
            severity = "critical" if kind in STATEFUL else "high"
            flag("REPLACE" if replace else "DELETE", severity, address,
                 ("Replacement" if replace else "Deletion") + " planned; verify dependencies, recovery and maintenance window.")
        if "forget" in actions:
            flag("FORGET", "high", address, "Resource leaves Terraform management; review lifecycle ownership.")
        after = change.get("after") or {}
        before = change.get("before") or {}
        # Scope CIDR checks to actual ingress fields, not arbitrary strings or egress.
        if kind == "aws_security_group":
            new_public = has_world_cidr(after.get("ingress", []))
            old_public = has_world_cidr(before.get("ingress", []))
        elif kind in {"aws_security_group_rule", "aws_vpc_security_group_ingress_rule"}:
            ingress = kind == "aws_vpc_security_group_ingress_rule" or after.get("type") == "ingress"
            new_public = ingress and has_world_cidr(after)
            old_public = has_world_cidr(before)
        else:
            new_public = old_public = False
        if new_public and not old_public:
            flag("PUBLIC_INGRESS", "high", address, "New internet-wide ingress detected; review ports and intended exposure.")
        if kind in STATEFUL and after.get("deletion_protection") is False and before.get("deletion_protection") is True:
            flag("PROTECTION_REMOVED", "critical", address, "Deletion protection is being disabled.")
        if truthy_unknown(change.get("after_unknown", {})):
            flag("UNKNOWN_VALUES", "unknown", address, "Some planned values are unknown; risk assessment is incomplete.")
    rank = {"critical": 4, "high": 3, "review": 2, "unknown": 1}
    rating = max((f["severity"] for f in findings), key=lambda s: rank[s], default="low")
    return {"changed_resources": summaries, "change_count": len(summaries), "risk_rating": rating,
            "findings": findings, "human_review_required": True,
            "limitations": ["Rating is a documented heuristic, not a failure probability.",
                            "Only listed resource-specific checks are implemented.",
                            "No raw plan values, variables, outputs or secrets are sent to the model."]}
