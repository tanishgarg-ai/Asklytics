import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.data_engine import get_schema, execute_query, execute_and_format_chart
from app.services.agent.state import AsklyticState

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.2,
    max_retries=6
)

def schema_retriever(state: AsklyticState) -> dict:
    """
    Retrieves the database schema for the workspace.

    Args:
        state (AsklyticState): The current conversational state.

    Returns:
        dict: A state update dictionary containing the 'dataset_schema'.
    """
    schema = get_schema(state["workspace_id"])
    return {"dataset_schema": schema}

def intent_analyzer(state: AsklyticState) -> dict:
    """
    Analyzes the user's query against the existing dashboard to determine the next action intent.

    Args:
        state (AsklyticState): The current conversational state.

    Returns:
        dict: A state update specifying 'agent_intent', 'agent_message', and potentially 'target_chart_index'.
    """
    if state.get("is_dashboard_init"):
        return {"agent_intent": "generate_new"}
        
    user_query = state.get("user_query", "")
    existing_dashboard = state.get("existing_dashboard", [])
    
    dashboard_summary = [
        {
            "id": i,
            "title": c.get("layout", {}).get("title", {}).get("text", "Untitled"),
            "data_traces": [trace.get("type") for trace in c.get("data", [])]
        }
        for i, c in enumerate(existing_dashboard)
    ]
    
    prompt = f"""You are an intelligent BI intent analyzer.
User Query: "{user_query}"

Existing Dashboard Charts:
{json.dumps(dashboard_summary, indent=2)}

Determine how to handle the query.
Return ONLY valid JSON matching this structure:
{{
  "intent": "follow_up" | "explain_existing" | "generate_new",
  "message": "If follow_up, write follow-up question here. If explain_existing, write a brief intro. If generate_new, leave blank.",
  "target_chart_index": <int or null> (if explain_existing, put the matching 'id' here)
}}
"""
    response = llm.invoke(prompt)
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:-3].strip()
    elif content.startswith("```"):
        content = content[3:-3].strip()
        
    try:
        parsed = json.loads(content)
        return {
            "agent_intent": parsed.get("intent", "generate_new"),
            "agent_message": parsed.get("message"),
            "target_chart_index": parsed.get("target_chart_index")
        }
    except Exception:
        return {"agent_intent": "generate_new"}

def query_generator(state: AsklyticState) -> dict:
    """
    Generates SQL queries and chart configurations based on the user's query and the data schema.

    Args:
        state (AsklyticState): The current conversational state, including schema and previous feedback.

    Returns:
        dict: A state update with 'generated_sql', 'chart_metadata', and any 'execution_error'.
    """
    schema = state.get("dataset_schema", {})
    user_query = state.get("user_query", "")
    is_dashboard_init = state.get("is_dashboard_init", False)
    feedback = state.get("reflection_feedback")
    
    schema_str = json.dumps(schema, indent=2)
    
    structure = """{
  "sql": "SELECT ...",
  "chart_type": "bar | line | scatter | pie | area",
  "x_column": "column_name",
  "y_column": "column_name",
  "title": "Descriptive chart title"
}"""
    
    if feedback:
        prompt = f"""You are an expert data analyst. Your previous SQL query failed to execute.
Schema: {schema_str}
Feedback: {feedback}
User Query: "{user_query}"

Generate a FIXED version.
You MUST return ONLY a JSON object (or array of objects if it was a dashboard init).
Each object must match this exact structure (no markdown):
{structure}
"""
    elif is_dashboard_init:
        prompt = f"""You are an expert data analyst. Based on this database schema:
{schema_str}

Create an initial dashboard consisting of 6 to 8 diverse and analytical charts that provide a comprehensive overview of the data.
You MUST return ONLY a strict JSON array of objects. Do not include any markdown formatting or explanation.
Each object must match this exact structure:
{structure}
"""
    else:
        prompt = f"""You are an expert data analyst. Based on this database schema:
{schema_str}

User query: "{user_query}"

Generate a SQL query and chart specification to answer this query.
You MUST return ONLY a strict JSON object. Do not include any markdown formatting or explanation.
The object must match this exact structure:
{structure}
"""
    
    response = llm.invoke(prompt)
    content = response.content.strip()
    
    if content.startswith("```json"):
        content = content[7:-3].strip()
    elif content.startswith("```"):
        content = content[3:-3].strip()
        
    try:
        parsed = json.loads(content)
    except Exception as e:
        return {"execution_error": f"Failed to parse LLM JSON output: {e}"}
        
    if is_dashboard_init and isinstance(parsed, list):
        sqls = [p.get("sql", "") for p in parsed]
        metadatas = parsed
        return {"generated_sql": sqls, "chart_metadata": metadatas, "execution_error": None}
    else:
        if isinstance(parsed, list) and not is_dashboard_init:
            parsed = parsed[0]
        return {
            "generated_sql": parsed.get("sql", ""), 
            "chart_metadata": parsed,
            "execution_error": None
        }

def validator(state: AsklyticState) -> dict:
    """
    Validates the generated SQL queries by attempting to execute them and format the chart payloads.

    Args:
        state (AsklyticState): The current conversational state containing generated SQL and metadata.

    Returns:
        dict: A state update with the 'plotly_json_payload' or an 'execution_error' if validation fails.
    """
    workspace_id = state["workspace_id"]
    is_dashboard_init = state.get("is_dashboard_init", False)
    sqls = state.get("generated_sql")
    metadatas = state.get("chart_metadata")
    
    if not sqls or not metadatas:
        return {"execution_error": "No SQL or metadata generated."}
        
    try:
        if is_dashboard_init:
            payloads = []
            for sql, meta in zip(sqls, metadatas):
                try:
                    payloads.append(execute_and_format_chart(workspace_id, sql, meta))
                except Exception as inner_e:
                    raise ValueError(f"Batch SQL error: {str(inner_e)}")
            return {"plotly_json_payload": payloads, "execution_error": None}
        else:
            payload = execute_and_format_chart(workspace_id, sqls, metadatas)
            return {"plotly_json_payload": payload, "execution_error": None}
            
    except Exception as e:
        return {"execution_error": str(e)}

def reflector(state: AsklyticState) -> dict:
    """
    Analyzes an execution error and prepares feedback to refine the SQL generation in the next retry.

    Args:
        state (AsklyticState): The current state containing the failed SQL and the execution error.

    Returns:
        dict: A state update with improved 'reflection_feedback' and incremented 'retry_count'.
    """
    bad_sql = state.get("generated_sql", "")
    error = state.get("execution_error", "")
    retry_count = state.get("retry_count", 0)
    
    return {
        "reflection_feedback": f"Bad SQL attempted: {json.dumps(bad_sql)} | Error produced: {error}",
        "retry_count": retry_count + 1
    }

def narration_generator(state: AsklyticState) -> dict:
    """
    Generates structured narrative explanation steps for a chart using the underlying datapoints.

    Args:
        state (AsklyticState): The current conversational state.

    Returns:
        dict: A state update containing 'narration_steps'.
    """
    intent = state.get("agent_intent", "generate_new")
    if intent == "follow_up":
        return {}
        
    target_idx = state.get("target_chart_index")
    current_charts = state.get("existing_dashboard", [])
    
    payload = None
    if intent == "explain_existing" and target_idx is not None and target_idx < len(current_charts):
        payload = current_charts[target_idx]
    elif intent == "generate_new":
        pl = state.get("plotly_json_payload")
        if isinstance(pl, list):
            return {} # Skip narration for full dashboard init
        payload = pl
        target_idx = len(current_charts) # New chart goes at the end
        
    if not payload:
        return {}
        
    data_summary = []
    if payload.get("data"):
        for trace in payload["data"]:
            x_vals = trace.get("x", [])[:5] 
            y_vals = trace.get("y", [])[:5]
            data_summary.append({"x_sample": x_vals, "y_sample": y_vals})
            
    prompt = f"""You are a data storyteller.
User Query: "{state.get('user_query', '')}"

Chart Data Snapshot (first 5 points):
{json.dumps(data_summary, indent=2)}

Generate 3-6 structured narration steps explaining this data based on the user's query.
Return ONLY valid JSON matching exactly this structure:
[
  {{
    "type": "chart",
    "text": "Brief one or two sentences explaining chart context.",
    "duration": 2500
  }},
  {{
    "type": "datapoint",
    "x": "Exact value from x_sample",
    "text": "Specific insight about this datapoint.",
    "duration": 2500
  }}
]
"""
    response = llm.invoke(prompt)
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:-3].strip()
    elif content.startswith("```"):
        content = content[3:-3].strip()
        
    try:
        parsed = json.loads(content)
        for step in parsed:
            step["target_id"] = f"chart_{target_idx}"
        return {"narration_steps": parsed}
    except Exception:
        return {"narration_steps": []}
