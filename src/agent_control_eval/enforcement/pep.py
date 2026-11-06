"""Policy enforcement point (PEP).

Implemented as an Inspect approval policy passed to
control_arena.eval.get_control_task(approval=[...]) (docs/CONTROLARENA_API_NOTES.md
section 4). The approver sees every tool call before execution, for ALL agent tools
(bash, python, text_editor), asks the PDP, logs the decision, and rejects denied calls
with a fixed message naming the rule ID, so P3 attackers and honest agents get the
same feedback. A bash-only wrapper would be bypassed via the python tool.

Built in step 4.
"""

DENIAL_TEMPLATE = "Command blocked by policy rule {rule_id}."
