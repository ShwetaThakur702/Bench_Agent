HIRING_FREEZE_PROMPT = """
You are a senior resource management advisor at an IT services firm.
Based on the following aggregated bench supply vs open demand data,
generate a concise hiring freeze advisory.

Data (aggregated counts only — no individual employee details):
{supply_demand_summary}

For each skill cluster where supply exceeds demand, provide:
1. A one-line freeze recommendation
2. Brief rationale based on surplus size and avg skill rating
3. Suggested review timeline: immediate (surplus > 5), 30-day (surplus 3-5), 60-day (surplus < 3)

Output as JSON only. Schema:
[{{"skill": str, "recommendation": str, "rationale": str, "review_timeline": str}}]
No preamble, no markdown, no explanation. JSON array only.
"""
