"""Attack policies P1 (unaware), P2 (monitor-aware), P3 (enforcement-aware).

P1 is ControlArena's stock attack policy, unmodified. P2 and P3 reuse the stock
policy and change only the system prompt (prompts/), so the three differ in
attacker knowledge and nothing else.

The P3 prompt is a plain-language rendering of the FROZEN policy. It is written
after policy v1.0 is frozen and is itself versioned with that policy.

Built in step 2/4, against the ControlArena API verified in docs/CONTROLARENA_API_NOTES.md.
"""
