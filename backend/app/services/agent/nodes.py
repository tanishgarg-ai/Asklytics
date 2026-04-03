import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.data_engine import get_schema, execute_query, execute_and_format_chart
from app.services.agent.state import AsklyticState

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.2
)

def schema_retriever(state: AsklyticState) -> dict:
    schema = get_schema(state["workspace_id"])
    return {"dataset_schema": schema}

def query_generator(state: AsklyticState) -> dict:
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
    bad_sql = state.get("generated_sql", "")
    error = state.get("execution_error", "")
    retry_count = state.get("retry_count", 0)
    
    return {
        "reflection_feedback": f"Bad SQL attempted: {json.dumps(bad_sql)} | Error produced: {error}",
        "retry_count": retry_count + 1
    }
