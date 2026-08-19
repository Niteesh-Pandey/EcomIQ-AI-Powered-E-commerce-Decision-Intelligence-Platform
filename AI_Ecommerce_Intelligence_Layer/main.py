from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from sql_queries import collect_sql_context
from python_analysis import collect_python_context
from ml_results import collect_ml_context
from ab_test_results import collect_ab_context

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").strip()
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "120000"))

SYSTEM_PROMPT = """
You are the AI Intelligence Layer of an e-commerce Customer, Revenue &
Growth Intelligence Platform.

VERIFIED_ANALYTICS is the source of truth.

Rules:
1. Use only evidence contained in VERIFIED_ANALYTICS.
2. Never invent a number, percentage, customer count, revenue amount,
   statistical result, causal claim, or model performance.
3. If evidence is insufficient, say "Insufficient evidence".
4. Do not confuse correlation/diagnostic evidence with proven causality.
5. Do not call an A/B test statistically significant unless the supplied
   result says it is significant.
6. Treat model scores as prioritization signals, not certainty.
7. Recommendations must be tied to evidence.
8. Give practical actions and KPIs.
9. When an experiment is relevant, suggest a concrete next test.
10. Keep the response business-friendly and concise.

Preferred format:
Executive Answer
Evidence
Root Cause / Drivers
Business Impact
Recommendation
Growth Action
KPI to Monitor
Suggested Experiment
Data Limitation (only when relevant)
"""

def json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if hasattr(obj, "item"):
        try: return obj.item()
        except Exception: pass
    if hasattr(obj, "isoformat"):
        try: return obj.isoformat()
        except Exception: pass
    return obj

def build_raw_context() -> dict:
    # Critical evidence is intentionally collected separately.
    return {
        "project": "AI-Powered E-commerce Customer, Revenue & Growth Intelligence Platform",
        "ml_predictions": collect_ml_context(),
        "ab_testing": collect_ab_context(),
        "sql_analytics": collect_sql_context(),
        "python_analytics": collect_python_context(),
    }

def _compact_section(section: Any, budget: int) -> Any:
    """Keep a section valid JSON; never cut a JSON string mid-object."""
    if budget <= 0:
        return {"status": "omitted", "reason": "context budget"}
    encoded = json.dumps(json_safe(section), ensure_ascii=False, indent=2, default=str)
    if len(encoded) <= budget:
        return section

    # Progressive compaction for large dicts.
    if isinstance(section, dict):
        compact = {}
        for key, value in section.items():
            piece = json.dumps(json_safe({key: value}), ensure_ascii=False, default=str)
            if len(json.dumps(compact, ensure_ascii=False, default=str)) + len(piece) <= budget:
                compact[key] = value
        if compact:
            compact["_context_note"] = "Large section compacted to preserve valid JSON and critical evidence."
            return compact

    if isinstance(section, list):
        result = []
        for item in section:
            candidate = json.dumps(json_safe(item), ensure_ascii=False, default=str)
            if len(json.dumps(result, ensure_ascii=False, default=str)) + len(candidate) <= budget:
                result.append(item)
            else:
                break
        return {"items": result, "_context_note": "List compacted."}

    return {"status": "omitted", "reason": "section exceeds budget"}

def route_question(question: str) -> list[str]:
    q = question.lower()
    routes = set()

    if any(x in q for x in ["checkout", "experiment", "a/b", "ab test", "variant", "ship"]):
        routes.add("ab_testing")
    if any(x in q for x in ["churn", "retention", "risk", "at-risk", "high risk"]):
        routes.update(["ml_predictions", "python_analytics"])
    if any(x in q for x in ["rfm", "segment", "customer value", "clv", "loyal", "champion"]):
        routes.update(["python_analytics", "sql_analytics", "ml_predictions"])
    if any(x in q for x in ["revenue", "sales", "aov", "order", "product", "category", "marketing", "cac", "funnel", "conversion", "cohort"]):
        routes.update(["sql_analytics", "python_analytics"])
    if any(x in q for x in ["forecast", "anomaly", "prediction", "predict"]):
        routes.add("python_analytics")
    if any(x in q for x in ["growth", "strategy", "recommend", "opportunity", "what should"]):
        routes.update(["sql_analytics", "python_analytics", "ml_predictions", "ab_testing"])

    if not routes:
        routes = {"ml_predictions", "ab_testing", "sql_analytics", "python_analytics"}

    # Critical sections first, regardless of dict insertion order.
    ordered = [x for x in ["ml_predictions", "ab_testing", "sql_analytics", "python_analytics"] if x in routes]
    return ordered

def build_verified_context(question: str | None = None) -> dict:
    raw = build_raw_context()
    sections = route_question(question or "")
    # Give critical compact sections guaranteed minimum space.
    minimum = {
        "ml_predictions": 6000,
        "ab_testing": 6000,
        "sql_analytics": 30000,
        "python_analytics": 30000,
    }

    selected = {"project": raw["project"], "question_routes": sections}
    remaining = MAX_CONTEXT_CHARS - len(json.dumps(selected, default=str)) - 500
    for name in sections:
        budget = min(max(minimum.get(name, 4000), 4000), max(remaining, 4000))
        value = _compact_section(raw[name], budget)
        selected[name] = value
        remaining -= len(json.dumps(json_safe(value), ensure_ascii=False, default=str))

    return selected

def save_context(context: dict) -> Path:
    out = BASE_DIR / "outputs" / "latest_verified_context.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(json_safe(context), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return out

def make_prompt(question: str, context: dict) -> str:
    return f"""VERIFIED_ANALYTICS:
{json.dumps(json_safe(context), ensure_ascii=False, indent=2, default=str)}

USER_QUESTION:
{question}

Answer only from the verified analytics above.
"""

def ask_gemini(question: str, context: dict) -> str:
    if MOCK_MODE:
        return "MOCK MODE: verified context assembled successfully. Set MOCK_MODE=false and add GEMINI_API_KEY to call Gemini."
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to .env.")
    if genai is None:
        raise RuntimeError("google-genai is not installed. Run: pip install -r requirements.txt")

    client = genai.Client(api_key=API_KEY)
    interaction = client.interactions.create(
        model=MODEL,
        input=make_prompt(question, context),
        system_instruction=SYSTEM_PROMPT,
    )
    text = getattr(interaction, "output_text", None)
    if not text:
        outputs = getattr(interaction, "outputs", None)
        if outputs:
            parts = []
            for item in outputs:
                candidate = getattr(item, "text", None)
                if candidate:
                    parts.append(candidate)
            text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("Gemini Interactions API returned an empty response.")
    return text

def main():
    print("=" * 72)
    print("AI-POWERED E-COMMERCE INTELLIGENCE LAYER")
    print("=" * 72)

    while True:
        try:
            question = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        context = build_verified_context(question)
        saved = save_context(context)
        size = saved.stat().st_size
        print(f"[OK] Routed verified context saved: {saved} ({size:,} bytes)")
        try:
            print("\nAI Analyst:\n")
            print(ask_gemini(question, context))
        except Exception as exc:
            print(f"[ERROR] {exc}")

if __name__ == "__main__":
    main()
