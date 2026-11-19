import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from state import TripState
from evals.rule_based import run_rule_evals
from evals.llm_judge import run_llm_evals


async def eval_node(state: TripState) -> dict:
    start = time.time()

    rule_scores = run_rule_evals(state)
    llm_scores = await run_llm_evals(state)

    eval_scores = {
        **rule_scores,
        **llm_scores,
        "passed": all(rule_scores.values()),
    }

    latency_ms = int((time.time() - start) * 1000)

    return {
        "eval_scores": eval_scores,
        "trajectory": [{
            "node": "eval",
            "rule_scores": rule_scores,
            "llm_scores": llm_scores,
            "passed": eval_scores["passed"],
            "latency_ms": latency_ms,
        }],
    }
