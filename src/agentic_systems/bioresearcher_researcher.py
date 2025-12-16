import langgraph.graph
from typing import TypedDict, List, Literal
from langchain_core.messages import BaseMessage

from langgraph.graph import StateGraph, START, END

try:
    from langgraph.prebuilt import create_react_agent
except ImportError:
    # newer stacks may expose an equivalent via langchain.agents
    from langchain.agents import create_agent as create_react_agent  # same idea: agent graph runnable

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

import os
from src.prompts.prompt_hub import prompt_hub
from src.tools.research_tools import research_tools

#define Agent State
class AgentState(TypedDict):
    # Control flow
    messages: List[BaseMessage]
    sender: str # for ReAct loops
    turn_count: int 

    # Junior Phase
    initial_hypotheses: List[str]

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
    scientific_context: str


agent_list = [
    "geneticist",
    "pharmacologist",
    "neurologist",
    "supervisor",
    "senior_protocol_designer",
    "peer_reviewer",
    "safety_reviewer",
    "principal_investigator",
    "final_evaluator",
    "hypothesis_refiner",
    "protocol_designer"
]

from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
config = {"configurable": {"thread_id": "user-123"}}

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

geneticist_agent = create_react_agent(model, tools=research_tools, name="geneticist", prompt=prompt_hub["geneticist"])
pharmacologist_agent = create_react_agent(model, tools=research_tools, name="pharmacologist", prompt=prompt_hub["pharmacologist"])
neurologist_agent = create_react_agent(model, tools=research_tools, name="neurologist", prompt=prompt_hub["neurologist"])
supervisor_agent   = create_react_agent(model, tools=[],   name="supervisor", prompt=prompt_hub["supervisor"])
senior_protocol_designer_agent = create_react_agent(model, tools=[],   name="senior_protocol_designer", prompt=prompt_hub["senior_protocol_designer"])
peer_reviewer_agent = create_react_agent(model, tools=[],   name="peer_reviewer", prompt=prompt_hub["peer_reviewer"])
safety_reviewer_agent = create_react_agent(model, tools=[],   name="safety_reviewer", prompt=prompt_hub["safety_reviewer"])
principal_investigator_agent = create_react_agent(model, tools=[],   name="principal_investigator", prompt=prompt_hub["principal_investigator"])
final_evaluator_agent = create_react_agent(model, tools=[],   name="final_evaluator", prompt=prompt_hub["final_evaluator"])
hypothesis_refiner_agent = create_react_agent(model, tools=[],   name="hypothesis_refiner", prompt=prompt_hub["hypothesis_refiner"])
protocol_designer_agent = create_react_agent(model, tools=[],   name="protocol_designer", prompt=prompt_hub["protocol_designer"])

agent_nodes = {
    "geneticist": geneticist_agent,
    "pharmacologist": pharmacologist_agent,
    "neurologist": neurologist_agent,
    "supervisor": supervisor_agent,
    "senior_protocol_designer": senior_protocol_designer_agent,
    "peer_reviewer": peer_reviewer_agent,
    "safety_reviewer": safety_reviewer_agent,
    "principal_investigator": principal_investigator_agent,
    "final_evaluator": final_evaluator_agent,
    "hypothesis_refiner": hypothesis_refiner_agent,
    "protocol_designer": protocol_designer_agent,
}

Class AIResearcherAgent(BaseModel):
    graph: StateGraph
    max_turns: int = 10
    def __init__(self, graph: StateGraph, max_turns: int = 10):
        self.graph = graph
        self.max_turns = max_turns

    def invoke(self, messages: List[BaseMessage], scientific_context: str):
        return self.graph.invoke({"messages": messages, "scientific_context": scientific_context})

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


def build_bioresearcher_agent_system(
    max_turns: int = 10

):
    workflow = StateGraph(AgentState)

    print("BioResearcher Agent System ")
    for agent_name in agent_list:
        workflow.add_node(agent_name, create_agent_node(agent_nodes[agent_name], agent_name))

   

    workflow.add_edge(START, "geneticist")
    # workflow.add_edge(START, "pharmacologist")
    # workflow.add_edge(START, "neurologist")


    workflow.add_edge("geneticist", "supervisor")
    workflow.add_edge("pharmacologist", "supervisor")
    workflow.add_edge("neurologist", "supervisor")

    #Supervisor to Seniors
    workflow.add_edge("supervisor", "hypothesis_refiner")
    workflow.add_edge("hypothesis_refiner", "protocol_designer")

    #Protocol to Reviewers
    workflow.add_edge("protocol_designer", "peer_reviewer")
    workflow.add_edge("peer_reviewer", "safety_reviewer")

    #Reviewers to Principal Investigator
    workflow.add_edge("safety_reviewer", "principal_investigator")

    # Safety Conditional edge
    workflow.add_conditional_edges("safety_reviewer",
    smart_route_based_on_safety_review,
     {
        "CRITICAL": "hypothesis_refiner", # start over
        "APPROVED": "principal_investigator", # approved handoff to Principal Investigator
        "MAJOR": "protocol_designer", # revise protocol
    })

    workflow.add_edge("principal_investigator", END)
   
    # workflow.add_edge("supervisor", "senior_protocol_designer")
    # workflow.add_edge("senior_protocol_designer", "peer_reviewer")

    graph = workflow.compile(checkpointer=checkpointer).graph()

    return graph


def protocol_evaluator(protocol, scientific_context):
    """Score protocol on 6 dimensions"""
    
    evaluator_llm = ChatOpenAI(model="mixtral-8x7b")
    
    prompt = f"""
    You are expert scientists evaluating this protocol:
    
    CONTEXT: {scientific_context}
    PROTOCOL: {protocol}
    
    Rate 0.0-1.0 on:
    - Novelty
    - Feasibility  
    - Impact
    - Clarity
    - Groundedness (evidence-based)
    - Efficiency
    """
    
    scores = evaluator_llm.evaluate(prompt)
    return scores
def get_weighted_reward(scores):
    """Combine scores with priorities"""
    return (
        0.10 * scores['novelty'] +
        0.20 * scores['feasibility'] +
        0.30 * scores['impact'] +      # Most important!
        0.15 * scores['clarity'] +
        0.20 * scores['groundedness'] +
        0.05 * scores['efficiency']
    )

def smart_route_based_on_safety_review(state: AgentState) -> Literal["CRITICAL", "APPROVED", "MAJOR"]:
    protocol = state["messages"][-1].content
    print(f"State: {state}")
    scientific_context = state["scientific_context"]
    scores = protocol_evaluator(protocol, scientific_context)
    reward = get_weighted_reward(scores)
    if reward > 0.7:
        return "APPROVED"
    elif reward > 0.5:
        return "MAJOR"
    else:
        return "CRITICAL"