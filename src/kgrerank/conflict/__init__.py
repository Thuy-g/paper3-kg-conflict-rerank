"""G2+ skeleton (working hypothesis, not a result): KG-first conflict typing with LLM fallback.

Signals are computed separately (signals.py); one explicit, versioned policy combines them
(policy.py); anything the policy cannot decide is UNKNOWN and may go to an LLM fallback (typer.py).
"""
