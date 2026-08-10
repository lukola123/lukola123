"""
Builds the ReAct Claim Coverage Evaluation Agent and provides a helper
to invoke it and parse a clean Decision/Reason response.
"""
import re
from langgraph.prebuilt import create_react_agent
from .config import get_chat_client
from .tools import get_claim_summary, check_claim_coverage

SYSTEM_PROMPT = """
You are an Insurance Claim Coverage Evaluation Agent.

You must use these tools in the following order:
1. get_claim_summary - Given a patient_id (e.g. "P001"), returns a combined
   summary of the patient's claim record AND their insurance policy's
   coverage rules in one call.
2. check_claim_coverage - Given the claim_summary text from step 1, evaluate
   each claimed procedure against the policy rules.

Important: only pass simple ID strings (like "P001") to get_claim_summary.
Do not attempt to pass full JSON objects or records as arguments.
Always invoke tools using the proper function-calling mechanism.
Never write out a tool call as JSON text in your response — actually call the tool.

Your final output must include:
- Decision: APPROVE or ROUTE FOR REVIEW
- Reason: A concise explanation citing age, gender, diagnoses, procedures, and policy requirements.

Important notes:
- You do not issue final denials.
- If all requirements are met -> APPROVE.
- If any requirement is not met -> ROUTE FOR REVIEW for human decision-making.
- Be clear and step-by-step in your reasoning.
""".strip()


def build_agent():
    chat_client = get_chat_client()
    tools = [get_claim_summary, check_claim_coverage]
    return create_react_agent(model=chat_client, tools=tools, prompt=SYSTEM_PROMPT)


def call_agent(agent, query: str) -> str:
    """Invoke the agent and return a clean:
    -Decision: Approved
    -Reason: ...
    """
    state = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"recursion_limit": 15},
    )

    text = ""
    if isinstance(state, dict) and state.get("messages"):
        msg = state["messages"][-1]
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        if isinstance(content, list):
            text = " ".join(str(c.get("text", "")) if isinstance(c, dict) else str(c) for c in content)
        else:
            text = str(content or "")

    t = text.replace("**", "").strip()
    dec = re.search(r"(?i)decision\s*[:\-]\s*(APPROVE|ROUTE\s+FOR\s+REVIEW)", t)
    rea = re.search(r"(?is)reason\s*[:\-]\s*(.+)", t)

    decision_norm = "Approved" if dec and dec.group(1).upper().startswith("APPROVE") else "Route for Review"
    reason = re.sub(r"\s+", " ", rea.group(1).strip()) if rea else t

    return f"Decision: {decision_norm}\n-Reason: {reason}"