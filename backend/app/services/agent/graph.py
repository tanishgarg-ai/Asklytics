from langgraph.graph import StateGraph, END
from app.services.agent.state import AsklyticState
from app.services.agent.nodes import schema_retriever, query_generator, validator, reflector

def should_reflect(state: AsklyticState) -> str:
    error = state.get("execution_error")
    retry_count = state.get("retry_count", 0)
    
    if error and retry_count < 3:
        return "reflector"
    return END

workflow = StateGraph(AsklyticState)

workflow.add_node("schema_retriever", schema_retriever)
workflow.add_node("query_generator", query_generator)
workflow.add_node("validator", validator)
workflow.add_node("reflector", reflector)

workflow.set_entry_point("schema_retriever")
workflow.add_edge("schema_retriever", "query_generator")
workflow.add_edge("query_generator", "validator")
workflow.add_conditional_edges("validator", should_reflect)
workflow.add_edge("reflector", "query_generator")

agent_executor = workflow.compile()
