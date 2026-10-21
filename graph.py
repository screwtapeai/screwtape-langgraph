"""LangGraph: workers -> consensus -> judge -> route on pass / retry / fail.

pip install -r requirements.txt
export SCREWTAPE_API_KEY=...
python graph.py

The three workers are stubs so the graph runs without an LLM key; replace draft() with your model call.
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from screwtape import consensus, judge

MAX_ATTEMPTS = 3


class State(TypedDict, total=False):
    task: str
    evidence: list[str]
    criteria: list[str]
    answers: list[dict]
    candidate: str
    risk: str
    verdict: dict
    feedback: list[str]
    attempts: int
    status: str


def draft(worker_id: str, state: State) -> str:
    # Replace with an LLM call. Pass state.get("feedback") into the prompt on a retry.
    return "The crew size was 4. The mission launched from Cape Canaveral."


def workers(state: State) -> dict:
    answers = [{"agent_id": w, "output": draft(w, state)} for w in ("alpha", "beta", "gamma")]
    return {"answers": answers, "attempts": state.get("attempts", 0) + 1}


def consensus_node(state: State) -> dict:
    c = consensus(state["task"], state["answers"])
    return {"candidate": c["consensus_answer"], "risk": c["false_consensus_risk"]}


def judge_node(state: State) -> dict:
    v = judge(state["task"], state["candidate"], state.get("evidence"), state.get("criteria"))
    return {"verdict": v, "feedback": v["reasons"]}


def route(state: State) -> str:
    verdict = state["verdict"]["verdict"]
    if verdict == "pass":
        return "accept"
    if verdict == "retry" and state.get("attempts", 0) < MAX_ATTEMPTS:
        return "workers"
    return "reject"


graph = StateGraph(State)
graph.add_node("workers", workers)
graph.add_node("consensus", consensus_node)
graph.add_node("judge", judge_node)
graph.add_node("accept", lambda s: {"status": "accepted"})
graph.add_node("reject", lambda s: {"status": "rejected"})
graph.add_edge(START, "workers")
graph.add_edge("workers", "consensus")
graph.add_edge("consensus", "judge")
graph.add_conditional_edges("judge", route, ["accept", "workers", "reject"])
graph.add_edge("accept", END)
graph.add_edge("reject", END)
app = graph.compile()

if __name__ == "__main__":
    out = app.invoke({
        "task": "State the crew size and launch site.",
        "evidence": ["The mission launched on 2024-03-01 from Cape Canaveral.", "The crew size was 4."],
        "criteria": ["crew size", "Cape Canaveral"],
    })
    print(out["status"], "risk:", out["risk"], "verdict:", out["verdict"]["verdict"], out["verdict"]["reasons"])
