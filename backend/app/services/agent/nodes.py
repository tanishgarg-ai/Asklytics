import os
import json
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.services.data_engine import get_schema, execute_query, execute_and_format_chart, get_or_create_session
from app.services.agent.state import AsklyticState

# --- LLM Pool ---
llm_sql = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.2,
    max_retries=3
)

llm_fast = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0,
    max_retries=3
)

llm_narrator = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
    max_retries=3
)

llm = llm_sql


def _truncate_schema(schema: dict, max_tables: int = 5, max_cols_per_table: int = 20) -> dict:
    """
    Trims the schema dict before sending to the SQL model.
    Cuts down token usage significantly on wide or multi-table databases.
    """
    truncated = {}
    for i, (table, cols) in enumerate(schema.items()):
        if i >= max_tables:
            break
        if isinstance(cols, list):
            truncated[table] = cols[:max_cols_per_table]
        elif isinstance(cols, dict):
            truncated[table] = dict(list(cols.items())[:max_cols_per_table])
        else:
            truncated[table] = cols
    return truncated


# --- Helper: Robust JSON extraction ---
def extract_json(content: str) -> dict | list:
    """Extracts JSON safely from messy LLM outputs."""
    content = content.strip()

    # Try markdown JSON block
    match = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", content, re.DOTALL)
    if match:
        content = match.group(1)
    else:
        # fallback: first JSON object/array
        match = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
        if match:
            content = match.group(1)

    return json.loads(content)


# --- Schema Retriever ---
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


# --- Intent Analyzer (FIXED) ---
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

    dashboard_summary = []
    for i, c in enumerate(existing_dashboard):
        # BUG FIX: Defensively handle string serialization issues to prevent AttributeError
        if isinstance(c, str):
            try:
                c = json.loads(c)
            except Exception:
                continue
        if not isinstance(c, dict):
            continue

        layout = c.get("layout", {}) if isinstance(c.get("layout"), dict) else {}

        title_obj = layout.get("title", "Untitled")
        title_text = title_obj.get("text", "Untitled") if isinstance(title_obj, dict) else str(title_obj)

        data_obj = c.get("data", [])
        data_traces = [trace.get("type") for trace in data_obj if isinstance(trace, dict)] if isinstance(data_obj,
                                                                                                         list) else []

        dashboard_summary.append({
            "id": i,
            "title": title_text,
            "data_traces": data_traces
        })

    prompt = f"""You are an intelligent Business Intelligence routing agent for Asklytics.
    Your job is to analyze a user's query and compare it against the charts currently visible on their dashboard.

    USER QUERY: "{user_query}"

Determine how to handle the query.
Return ONLY valid JSON matching this structure:
{{
  "intent": "follow_up" | "explain_existing" | "generate_new",
  "message": "If follow_up, write follow-up question here. If explain_existing, write a brief intro. If generate_new, leave blank.",
  "target_chart_index": <int or null> (if explain_existing, put the matching 'id' here)
}}
"""
    response = llm.invoke([prompt])

    # Extract content safely
    if isinstance(response.content, list):
        # Join all text blocks if there are multiple, or just take the first
        raw_text = "".join([block["text"] for block in response.content if block["type"] == "text"])
    else:
        raw_text = response.content

    content = raw_text.strip()
    try:
        parsed = extract_json(content)
        return {
            "agent_intent": parsed.get("intent", "generate_new"),
            "agent_message": parsed.get("message"),
            "target_chart_index": parsed.get("target_chart_index")
        }
    except Exception as e:
        print("Intent parsing failed:", content)
        return {"agent_intent": "generate_new"}


def query_generator(state: AsklyticState) -> dict:
    """
    Generates SQL queries and chart configurations based on the user's query and the data schema.
    Applies heuristic chart selection based on the Doc2Chart research paper.

    Args:
        state (AsklyticState): The current conversational state, including schema and previous feedback.

    Returns:
        dict: A state update with 'generated_sql', 'chart_metadata', and any 'execution_error'.
    """
    schema = state.get("dataset_schema", {})
    user_query = state.get("user_query", "")
    is_dashboard_init = state.get("is_dashboard_init", False)
    feedback = state.get("reflection_feedback")

    # Truncate schema to reduce token cost — wide DBs can easily blow the context
    schema = _truncate_schema(schema)
    schema_str = json.dumps(schema, indent=2)

    structure = """{
  "sql": "SELECT ...",
  "chart_type": "bar | line | scatter | pie | area",
  "x_column": "column_name",
  "y_column": "column_name",
  "title": "Descriptive chart title"
}"""

    # Added Heuristics from Doc2Chart Research Paper
    heuristics = """
CHART SELECTION HEURISTICS:
- Time-based/Trend (4+ data points): Use 'line'
- Time-based/Trend (<4 data points): Use 'bar'
- Comparison/Magnitude (2-5 categories): Use 'bar'
- Comparison/Magnitude (6+ categories): Use 'bar' (horizontal) or 'scatter'
- Composition/Proportions (<= 6 segments): Use 'pie'
"""

    if feedback:
        prompt = f"""You are an expert data analyst. Your previous SQL query failed to execute.
Schema: {schema_str}
Feedback: {feedback}
User Query: "{user_query}"

Generate a FIXED version.
{heuristics}
You MUST return ONLY a JSON object (or array of objects if it was a dashboard init).
Each object must match this exact structure (no markdown):
{structure}
"""
    elif is_dashboard_init:
        prompt = f"""You are an expert data analyst. Based on this database schema:
{schema_str}

Create an initial dashboard consisting of 6 to 8 diverse and analytical charts that provide a comprehensive overview of the data.
{heuristics}
You MUST return ONLY a strict JSON array of objects. Do not include any markdown formatting or explanation.
Each object must match this exact structure:
{structure}
"""
    else:
        prompt = f"""You are an expert data analyst. Based on this database schema:
{schema_str}

User query: "{user_query}"
"""
        current_table = state.get("current_table")
        if current_table:
            prompt += f"\nCRITICAL: You MUST use the cleaned table '{current_table}' for this query.\n"

        prompt += f"""
Generate a SQL query and chart specification to answer this query.
{heuristics}
You MUST return ONLY a strict JSON object. Do not include any markdown formatting or explanation.
The object must match this exact structure:
{structure}
"""

    # llm_sql: SQL generation needs the most capable model
    response = llm_sql.invoke([prompt])
    content = response.content if isinstance(response.content, str) else \
        "".join([b.get("text", "") for b in response.content if isinstance(b, dict)])
    content = content.strip()

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
    Applies criteria from InsightEval research to generate high-quality insights.

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
            return {}  # Skip narration for full dashboard init
        payload = pl
        target_idx = len(current_charts)  # New chart goes at the end

    if not payload:
        return {}

    data_summary = []
    if isinstance(payload.get("data"), list):
        for trace in payload.get("data"):
            if isinstance(trace, dict):
                is_pie = trace.get("type") == "pie"
                x_vals = list(trace.get("labels" if is_pie else "x") or [])[:15]
                y_vals = list(trace.get("values" if is_pie else "y") or [])[:15]
                data_summary.append({
                    "x_sample": x_vals, 
                    "y_sample": y_vals, 
                    "type": trace.get("type")
                })

    prompt = f"""You are an expert data storyteller.
User Query: "{state.get('user_query', '')}"

Chart Data Snapshot (selected points):
{json.dumps(data_summary, indent=2)}

Generate 3-6 structured narration steps explaining this data based on the user's query.
CRITICAL: Ensure the insights are quantitative, informative, non-trivial, and concise (based on InsightEval criteria). 
Do not just state the obvious; highlight underlying patterns, extremes, or meaning.

Return ONLY valid JSON matching exactly this structure:
[
  {{
    "type": "chart",
    "text": "Brief one or two sentences explaining chart context and key pattern.",
    "duration": 2500
  }},
  {{
    "type": "datapoint",
    "x": "Exact value from x_sample",
    "text": "Specific, non-trivial quantitative insight about this datapoint.",
    "duration": 2500
  }}
]
"""
    response = llm.invoke([prompt])

    # Extract content safely
    if isinstance(response.content, list):
        # Join all text blocks if there are multiple, or just take the first
        raw_text = "".join([block["text"] for block in response.content if block["type"] == "text"])
    else:
        raw_text = response.content

    content = raw_text.strip()

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


# --- Data Preparation Operators (DeepPrep Style) ---

def drop_na(workspace_id: str, table: str) -> str:
    conn = get_or_create_session(workspace_id)
    new_table = f"{table}_dna"
    cols = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    col_names = [c[1] for c in cols]
    where_clause = " AND ".join([f"{c} IS NOT NULL" for c in col_names])
    conn.execute(f"CREATE OR REPLACE TABLE {new_table} AS SELECT * FROM {table} WHERE {where_clause}")
    return new_table


def cast_column_types(workspace_id: str, table: str) -> str:
    conn = get_or_create_session(workspace_id)
    new_table = f"{table}_cast"
    # Basic casting simulation: ensure all numeric-looking columns are cast from varchar if possible
    conn.execute(f"CREATE OR REPLACE TABLE {new_table} AS SELECT * FROM {table}")
    return new_table


def split_column(workspace_id: str, table: str, column: str) -> str:
    conn = get_or_create_session(workspace_id)
    new_table = f"{table}_split_{column}"
    conn.execute(
        f"CREATE OR REPLACE TABLE {new_table} AS SELECT *, split_part({column}, ' ', 1) as {column}_prefix FROM {table}")
    return new_table


def aggregate_table(workspace_id: str, table: str, group_by: list, metrics: dict) -> str:
    conn = get_or_create_session(workspace_id)
    new_table = f"{table}_agg"
    agg_cols = ", ".join([f"{func}({col}) as {col}_{func}" for col, func in metrics.items()])
    group_cols = ", ".join(group_by)
    conn.execute(
        f"CREATE OR REPLACE TABLE {new_table} AS SELECT {group_cols}, {agg_cols} FROM {table} GROUP BY {group_cols}")
    return new_table


def join_tables(workspace_id: str, table_a: str, table_b: str, key: str) -> str:
    conn = get_or_create_session(workspace_id)
    new_table = f"{table_a}_joined_{table_b}"
    conn.execute(
        f"CREATE OR REPLACE TABLE {new_table} AS SELECT a.*, b.* EXCLUDE ({key}) FROM {table_a} a JOIN {table_b} b ON a.{key} = b.{key}")
    return new_table


def data_prep_node(state: AsklyticState) -> dict:
    """
    Applies sequential data cleaning transformations with rollback logic on data loss,
    inspired by the DeepPrep framework's execution-grounded reasoning.
    """
    workspace_id = state["workspace_id"]
    current_table = state.get("current_table")

    if not current_table:
        schema = state.get("dataset_schema", {})
        if not schema:
            return {"prep_status": "failed", "execution_error": "No schema found for data prep."}
        current_table = list(schema.keys())[0]

    history = state.get("transformation_history", [])
    row_counts = state.get("row_count_history", [])

    conn = get_or_create_session(workspace_id)
    initial_count = conn.execute(f"SELECT COUNT(*) FROM {current_table}").fetchone()[0]

    if not history:
        row_counts = [initial_count]

    # Transformation Pipeline
    steps = [
        ("cast_column_types", []),
        ("drop_na", []),
    ]

    new_history = list(history)
    new_row_counts = list(row_counts)
    active_table = current_table

    for step_name, _ in steps:
        if step_name in new_history:
            continue

        prev_table = active_table
        prev_count = new_row_counts[-1]

        try:
            if step_name == "drop_na":
                active_table = drop_na(workspace_id, prev_table)
            elif step_name == "cast_column_types":
                active_table = cast_column_types(workspace_id, prev_table)

            current_count = conn.execute(f"SELECT COUNT(*) FROM {active_table}").fetchone()[0]

            # Rollback check: >50% data loss triggers rollback of the LAST step
            if current_count < (prev_count * 0.5):
                active_table = prev_table
                new_history.append(f"{step_name} (ROLLBACKED: Data Loss > 50%)")
                break
            else:
                new_history.append(step_name)
                new_row_counts.append(current_count)

        except Exception as e:
            active_table = prev_table
            new_history.append(f"{step_name} (FAILED: {str(e)})")
            break

    return {
        "current_table": active_table,
        "transformation_history": new_history,
        "row_count_history": new_row_counts,
        "prep_status": "success",
        "dataset_schema": get_schema(workspace_id)
    }
