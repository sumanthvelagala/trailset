from langgraph.graph import StateGraph, END

from state import TripState
from nodes.scout import scout_node


def build_graph():
    graph = StateGraph(TripState)

    graph.add_node("scout", scout_node)
    # planner and eval nodes added in Day 3 and Day 4
    graph.set_entry_point("scout")
    graph.add_edge("scout", END)

    return graph.compile()


trip_graph = build_graph()
