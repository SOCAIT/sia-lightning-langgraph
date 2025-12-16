import langgraph.graph
from typing import TypedDict, List, Literal
from langchain_core.messages import BaseMessage

from langgraph.graph import StateGraph, START, END

try:
    from langgraph.prebuilt import create_react_agent
except ImportError:
    # newer stacks may expose an equivalent via langchain.agents
    from langchain.agents import create_agent as create_react_agent  # same idea: agent graph runnable

from lanf
from dotenv import load_dotenv
load_dotenv()

import os

#define Agent State
class AgentState(TypedDict):
    # Control flow
    messages: List[BaseMessage]
    sender: str # for ReAct loops
    turn_count: int 

    # Junior Phase
    initial hypotheses: List[str]

    # Supervisor Phase
    selected_hypothesis: dict

    # Senior Phase
    experimental_protocol: dict

    # Review Phase
    peer_review: str
    safety_review: str

    # final output
    final_decision: str
    final_evaluation: str


agent_list = [
    "Geneticist",
    "Pharmacologist",
    "Neurologist",
    "Supervisor"
    "HypothesisRefiner",
    "ProtocolDesigner",
    "PeerReviewer",
    "SafetyOfficer",
    "PrincipalInvestigator",
]

from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
config = {"configurable": {"thread_id": "user-123"}}

config = {"configurable": {"thread_id": "user-123"}}

def build_research_agent():
    workflow = StateGraph(AgentState)

from langchain_core.runnables import RunnableConfig

def create_agent_node(agent_graph, agent_name: str):
    def node(state, config: RunnableConfig):
        thread_id = config["configurable"]["thread_id"]

        # per-agent memory namespace
        agent_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": agent_name,
            }
        }

       
        last_user_turn = state["messages"][-1:]

        out = agent_graph.invoke({"messages": last_user_turn}, agent_config)

        # return only the new assistant message back to the parent state
        return {"messages": [out["messages"][-1]]}

    return node