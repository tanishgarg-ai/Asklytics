from langgraph.graph import StateGraph, END
from app.services.agent.state import AsklyticState
from app.services.agent.nodes import schema_retriever, intent_analyzer, query_generator, validator, reflector, narration_generator

def route_intent(state: AsklyticState) -> str:
    """
    Determines the next node in the graph based on the agent's determined intent.

    Args:
        state (AsklyticState): The current conversational state.

    Returns:
        str: The name of the next node or `END` to terminate.
    """
    intent = state.get("agent_intent")
    if intent == "follow_up":
        return END
    elif intent == "explain_existing":
        return "narration_generator"
    return "query_generator" # generate_new

def should_reflect(state: AsklyticState) -> str:
    """
    Decides whether to trigger the reflector node to correct SQL errors based on retry logic.

    Args:
        state (AsklyticState): The current state tracking execution errors.

    Returns:
        str: 'reflector' if under retry limits with an error, otherwise 'narration_generator'.
    """
    error = state.get("execution_error")
    retry_count = state.get("retry_count", 0)
    
    if error and retry_count < 3:
        return "reflector"
    return "narration_generator"

workflow = StateGraph(AsklyticState)

workflow.add_node("schema_retriever", schema_retriever)
workflow.add_node("intent_analyzer", intent_analyzer)
workflow.add_node("query_generator", query_generator)
workflow.add_node("validator", validator)
workflow.add_node("reflector", reflector)
workflow.add_node("narration_generator", narration_generator)

workflow.set_entry_point("schema_retriever")
workflow.add_edge("schema_retriever", "intent_analyzer")
workflow.add_conditional_edges("intent_analyzer", route_intent)
workflow.add_edge("query_generator", "validator")
workflow.add_conditional_edges("validator", should_reflect)
workflow.add_edge("reflector", "query_generator")
workflow.add_edge("narration_generator", END)

agent_executor = workflow.compile()
