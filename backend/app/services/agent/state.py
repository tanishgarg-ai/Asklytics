from typing import TypedDict, Optional, Union, List

class AsklyticState(TypedDict):
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
