import streamlit as st
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
import sqlite3
from langchain_groq import ChatGroq
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Simple SQL Chat", page_icon="🦜")
st.title("🦜 Simple SQL Chat with Database")

# --- Database selection ---
db_options = ["SQLite (local student.db)", "Remote MySQL"]
selected_db = st.sidebar.radio("Choose Database", db_options)

# --- LLM API key ---
api_key = st.sidebar.text_input("Groq API Key", type="password", value=os.getenv("GROQ_API_KEY", ""))
if not api_key:
    st.info("Please enter Groq API Key")
    st.stop()

llm = ChatGroq(groq_api_key=api_key, model_name="llama-3.1-8b-instant", streaming=True)

# --- Configure database ---
engine = None
schema_info = ""

def get_schema_info(_engine):
    if _engine is None:
        return ""
    try:
        inspector = inspect(_engine)
        tables = inspector.get_table_names()
        if not tables:
            return "The database is empty (no tables found)."
        
        info = "The database has the following tables: " + ", ".join(tables)
        for table in tables:
            columns = [col['name'] for col in inspector.get_columns(table)]
            info += f"\nTable '{table}' has columns: " + ", ".join(columns)
        return info
    except Exception as e:
        return f"Error fetching schema: {e}"

if selected_db == "SQLite (local student.db)":
    db_path = (Path(__file__).parent / "student.db").absolute()
    if not db_path.exists():
        st.error(f"Database not found: {db_path}")
        st.stop()
    creator = lambda: sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    engine = create_engine("sqlite:///", creator=creator)
    schema_info = get_schema_info(engine)

else:  # MySQL
    mysql_host = st.sidebar.text_input("MySQL Host", value="localhost")
    mysql_user = st.sidebar.text_input("MySQL User", value="root")
    mysql_password = st.sidebar.text_input("MySQL Password", type="password")
    mysql_db = st.sidebar.text_input("MySQL Database Name")
    
    if not (mysql_host and mysql_user and mysql_password and mysql_db):
        st.info("Provide all MySQL connection details")
        st.stop()
    
    conn_str = f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"
    engine = create_engine(conn_str)
    schema_info = get_schema_info(engine)

# --- Chat session state ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Hello! Ask me anything about the database."}]

if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = [{"role": "assistant", "content": "History cleared. Ask me something new!"}]
    st.rerun()

# Display chat history
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- User input ---
user_query = st.chat_input("Ask a question about the database...")

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    # --- Generate SQL ---
    prompt = f"""
    You are an expert SQL assistant. Use the following database schema information:
    {schema_info}
    
    Convert this natural language question into a valid SQL query.
    Question: {user_query}
    
    Return ONLY the raw SQL query. No explanation, no backticks, no Markdown formatting.
    """
    try:
        response = llm.invoke(prompt)
        sql_query = response.content.strip()
        # Clean up in case model ignored instruction
        if "```" in sql_query:
            sql_query = sql_query.split("```")[1]
            if sql_query.lower().startswith("sql"):
                sql_query = sql_query[3:].strip()
            sql_query = sql_query.strip()
    except Exception as e:
        st.error(f"Error generating SQL: {e}")
        st.stop()

    # --- Execute SQL ---
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = result.fetchall()
            
            with st.chat_message("assistant"):
                st.code(sql_query, language="sql")
                if rows:
                    df = pd.DataFrame(rows, columns=result.keys())
                    st.dataframe(df)
                    st.write(f"Found {len(rows)} records.")
                    st.session_state.messages.append({"role": "assistant", "content": f"Query: `{sql_query}`\n\nResults found."})
                else:
                    st.info("No records found for that query.")
                    st.session_state.messages.append({"role": "assistant", "content": f"Query: `{sql_query}`\n\nNo records found."})
    except Exception as e:
        error_msg = f"Error executing SQL: {e}"
        st.error(error_msg)
        st.code(sql_query, language="sql")
        st.session_state.messages.append({"role": "assistant", "content": f"SQL Error with query: `{sql_query}`"})