from typing import Dict, List


def get_playbooks() -> Dict[str, Dict]:
    """Return tactical playbooks for L1–L3 staff roles."""
    return {
        "level_1": {
            "role": "Junior triage",
            "sla_seconds": [30, 90],
            "checklist": [
                "Is the claim verifiable in principle? (objective, falsifiable)",
                "Any indicators of immediate harm? (health, safety, democratic process)",
                "Virality vector present? (views, growth, followers)",
                "Astro-Score available? If ≥ 8 → escalate; 5–7.99 → semi",
                "If unverifiable or satire → tag and archive",
            ],
            "templates": {
                "acknowledge": "Thanks for raising this. We’re checking verified sources and will update shortly.",
                "debunk_short": "Context: {source}. No evidence supports this claim. More: {link}",
                "escalate_note": "Escalating due to risk/virality/astro-score thresholds",
            },
        },
        "level_2": {
            "role": "Senior analyst",
            "focus": [
                "Network graph review (clusters, synchronized behavior)",
                "Source validation (independent corroboration, credibility)",
                "Prepare concise public report (what, evidence, impact, action)",
            ],
            "artifacts": [
                "Compact network graph (PNG/JSON)",
                "Top-5 corroborating sources (links, quotes)",
                "Proposed verdict (true/misleading/unsupported/manipulated)",
                "Prefilled reply templates (persona-aligned)",
            ],
        },
        "level_3": {
            "role": "Investigator",
            "scope": [
                "Cross-platform aggregation (IDs, timestamps, hashes)",
                "Legal/forensic steps (where appropriate and lawful)",
                "Platform notification package (if coordinated harm)",
            ],
            "deliverables": [
                "Investigative report (timeline, actors, evidence)",
                "Counter-content plan (avatar post scheduling)",
                "Audit bundle (snapshots + hashes + exportable JSON)",
            ],
        },
    }


def get_playbook(level: int) -> Dict:
    mapping = {1: "level_1", 2: "level_2", 3: "level_3"}
    return get_playbooks()[mapping.get(level, "level_1")]



