from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.models import get_chat_model
from app.tools import get_tool_belt

SYSTEM_PROMPT = (
    "You are a helpful assistant specialized in feline (cat) health. "
    "Use the retrieve_information tool for cat-health questions, web search for "
    "current information, and Arxiv for research papers. Cite tool results when "
    "they inform your answer."
)

# Safe loop limit — stop re-answering after this many attempts even if the judge
# is still unsatisfied, so a persistently "unhelpful" answer can't loop forever.
MAX_ATTEMPTS = 3


class HelpfulnessState(TypedDict):
    messages: Annotated[list, add_messages]
    attempts: int  # how many times the agent node has answered
    helpful: bool  # latest judge verdict (for routing + Studio visibility)
    reason: str  # judge's justification for the latest verdict


class Verdict(BaseModel):
    helpful: bool = Field(
        description="True if the answer fully and helpfully addresses the user's question."
    )
    reason: str = Field(description="Brief justification for the verdict.")


def _build_inner_agent():
    # Mirrors app/graphs/simple_agent.py — a prebuilt ReAct agent that owns the
    # tool-calling loop. We wrap it as a single node in the outer graph below.
    from langchain.agents import create_agent

    return create_agent(
        model=get_chat_model(),
        tools=get_tool_belt(),
        system_prompt=SYSTEM_PROMPT,
    )


_inner_agent = _build_inner_agent()

JUDGE_PROMPT = (
    "You are a strict quality judge for a feline-health assistant. Given the user's "
    "question and the assistant's answer, decide whether the answer is genuinely "
    "helpful: does it directly and completely address the question with accurate, "
    "specific, actionable information? Mark it unhelpful if it is vague, evasive, "
    "off-topic, or leaves the core question unanswered."
)


def agent_node(state: HelpfulnessState) -> dict:
    prior = state["messages"]
    result = _inner_agent.invoke({"messages": prior})
    # The inner agent returns the full accumulated transcript; keep only the
    # messages produced this turn so add_messages doesn't duplicate the input.
    new_messages = result["messages"][len(prior):]
    return {
        "messages": new_messages,
        "attempts": state.get("attempts", 0) + 1,
    }


def judge_node(state: HelpfulnessState) -> dict:
    messages = state["messages"]

    question = next(
        (m.content for m in messages if isinstance(m, HumanMessage)),
        "",
    )
    answer = next(
        (
            m.content
            for m in reversed(messages)
            if isinstance(m, AIMessage) and m.content
        ),
        "",
    )

    judge = get_chat_model(temperature=0).with_structured_output(Verdict)
    verdict: Verdict = judge.invoke(
        [
            {"role": "system", "content": JUDGE_PROMPT},
            {
                "role": "human",
                "content": f"Question:\n{question}\n\nAnswer:\n{answer}",
            },
        ]
    )
    return {"helpful": verdict.helpful, "reason": verdict.reason}


def route_after_judge(state: HelpfulnessState) -> str:
    if state.get("helpful") or state.get("attempts", 0) >= MAX_ATTEMPTS:
        return END
    return "agent"


builder = StateGraph(HelpfulnessState)
builder.add_node("agent", agent_node)
builder.add_node("judge", judge_node)
builder.add_edge(START, "agent")
builder.add_edge("agent", "judge")
builder.add_conditional_edges(
    "judge", route_after_judge, {"agent": "agent", END: END}
)

graph = builder.compile()
