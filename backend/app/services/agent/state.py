from typing import TypedDict, Optional, Union, List

class AsklyticState(TypedDict):
    """
    Defines the shape of the graph state used by the LangGraph agent.

    Maintains contextual data across conversational turns, SQL generation passes, 
    and reflection iterations.
    """
    workspace_id: str
    user_query: str
    dataset_schema: dict
    generated_sql: Union[str, List[str]]
    chart_metadata: Union[dict, List[dict]]
    plotly_json_payload: Union[dict, List[dict]]
    execution_error: Optional[str]
    retry_count: int
    is_dashboard_init: bool
    reflection_feedback: Optional[str]
    narration_steps: Optional[List[dict]]
    existing_dashboard: Optional[List[dict]]
    agent_intent: Optional[str]
    agent_message: Optional[str]
    target_chart_index: Optional[int]
