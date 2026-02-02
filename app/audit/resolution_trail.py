from app.models.resolution_model import ResolutionAgentOutput


def log_resolution_agent_results(result: ResolutionAgentOutput):
    """
    Standardized logger for the Resolution Recommendation Agent.
    Provides the final verdict, risk assessment, and approval checklist.
    """
    # Visual configuration for different outcomes
    banners = {
        "auto_approve": ("🟢", "AUTO-APPROVE"),
        "flag_for_review": ("🟡", "FLAG FOR REVIEW"),
        "escalate_to_human": ("🔴", "ESCALATE TO HUMAN"),
    }
    icon, verdict_label = banners.get(result.recommended_action, ("⚪", "UNKNOWN"))

    print("\n" + "═" * 60)
    print(f"{icon} {verdict_label} VERDICT {icon}".center(60))
    print("═" * 60)

    # 1. Primary Decision Metrics
    print(f"\nFINAL ACTION:  {result.recommended_action.upper()}")
    print(f"RISK LEVEL:    {result.risk_level.upper()}")
    print(f"DECISION CONF: {result.confidence:.2%}")
    print(
        f"HUMAN REVIEW:  {'REQUIRED' if result.human_review_required else 'NOT REQUIRED'}"
    )

    # 2. Approval Checklist
    print(f"\n[APPROVAL CRITERIA CHECKLIST]")
    all_possible_criteria = [
        "exact_po_match",
        "all_items_match",
        "high_extraction_confidence",
        "verified_supplier",
        "zero_variance",
    ]

    for criterion in all_possible_criteria:
        met = criterion in result.approval_criteria_met
        status_char = "✅" if met else "❌"
        # Format the criterion string for better readability
        label = criterion.replace("_", " ").title()
        print(f"  {status_char} {label}")

    # 3. Decision Logic & Reasoning
    print(f"\n[FINAL AUDIT REASONING]")
    # Splitting reasoning into lines for clean terminal wrap if it's long
    import textwrap

    wrapped_reasoning = textwrap.fill(result.reasoning, width=54)
    for line in wrapped_reasoning.split("\n"):
        print(f"  {line}")

    # 4. Final Disposition
    print(f"\nSTATUS SUMMARY:")
    if result.recommended_action == "auto_approve":
        print("  🚀 System has authorized automatic payment processing.")
    elif result.recommended_action == "flag_for_review":
        print("  🔎 Held for manual verification of minor variances.")
    else:
        print("  🚨 Hard stop triggered. Immediate human intervention required.")

    print("\n" + "═" * 60 + "\n")
