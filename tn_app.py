import streamlit as st
import sqlite3
import google.generativeai as genai
import pandas as pd

# ==========================================
# 1. AI ENGINE AUTHORIZATION SETUP
# ==========================================
# Replace with your actual key from Google AI Studio
GEMINI_API_KEY = "AIzaSyC7_RuEV_Bdd-TskiS-iRCHcQrnOzLdBuA" 
genai.configure(api_key=GEMINI_API_KEY)

## ==========================================
# 2. CLOUD DATABASE EXECUTION ROUTER
# ==========================================
# 🌟 CHANGE: Completely replaced the local SQLite router with this Snowflake router!
def execute_database_query(sql_script):
    try:
        conn = snowflake.connector.connect(
            user=st.secrets["snowflake"]["user"],
            password=st.secrets["snowflake"]["Thanksuniverse@123"],
            account=st.secrets["snowflake"]["MIOCYXM-BD44077"],
            warehouse=st.secrets["snowflake"]["COMPUTE_WH"],
            database=st.secrets["snowflake"]["TN_ELECTIONS"],
            schema=st.secrets["snowflake"]["public"]
        )
        cursor = conn.cursor()
        cursor.execute(sql_script)
        headers = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()
        conn.close()
        return headers, records
    except Exception as error:
        return None, str(error)

# ==========================================
# 3. TEXT-TO-SQL CONTEXT ENGINEERING PROMPT
# ==========================================
SYSTEM_CONTEXT = """
You are an expert SQL translation agent for a Tamil Nadu Election Dataset (State S22, May 2026).
Your sole job is to read the user's natural language question and output ONLY a valid, executable SQLite query based on these tables:

1. Table: constituencies_enriched
   Columns: constituency_id, state_code, ac_no, constituency_code, constituency_name, state_name, district_id, district_no, district_name, male_electors, female_electors, third_gender_electors, total_electors, current_round, total_rounds, round_progress, status_text, total_evm_votes, total_postal_votes, total_votes, turnout_percent, candidate_count, leader_candidate_id, leader_candidate, leader_party_id, leader_party, leader_party_abbreviation, leader_status, leader_votes, leader_vote_share_percent, runner_up_candidate_id, runner_up_candidate, runner_up_party_id, runner_up_party, runner_up_party_abbreviation, runner_up_status, runner_up_votes, runner_up_vote_share_percent, third_candidate_id, third_candidate, third_party_id, third_party, third_party_abbreviation, third_votes, third_vote_share_percent, margin, runner_up_margin, nota_candidate_id, nota_votes, nota_share_percent, official_status, official_margin, official_leading_candidate, official_leading_party, official_trailing_candidate, official_trailing_party

2. Table: candidates_enriched
   Columns: candidate_id, constituency_id, state_code, ac_no, constituency_code, constituency_name, district_no, district_name, serial_no, candidate_name, normalized_name, party_id, party, party_abbreviation, is_nota, rank, status, raw_status_text, evm_votes, postal_votes, total_votes, card_votes, effective_votes, vote_share_percent, votes_behind_leader, constituency_margin, constituency_runner_up_margin, constituency_total_votes, current_round, total_rounds

3. Table: party_state_summary
   Columns: party_id, party, normalized_name, abbreviation, candidate_count, contested_constituencies, top_count, won_count, leading_count, lost_count, second_place_count, third_place_count, total_votes, vote_share_percent, avg_candidate_vote_share_percent, avg_rank, best_rank, smallest_lead, avg_lead, biggest_lead, smallest_deficit, avg_deficit, biggest_deficit

4. Table: district_summary
   Columns: district_id, state_code, district_no, district_name, official_constituency_count, male_electors, female_electors, third_gender_electors, total_electors, scraped_constituencies, votes_cast, turnout_percent, avg_margin, closest_margin, biggest_margin, close_under_500, close_under_1000

RULES:
- Return ONLY the executable SQL query string. Do NOT add any conversational explanation, intro, or markdown backticks blocks.
- The query MUST begin directly with the keyword SELECT.
- Always use the 'LIKE' operator with wildcards for text queries (e.g., constituency_name LIKE '%PERAMBUR%') to handle variations in user input.
"""

# ==========================================
# 4. INTERFACE RENDERING LAYER (STREAMLIT)
# ==========================================
st.set_page_config(page_title="TN Election AI Analyst", layout="wide")
st.title("🗳️ Tamil Nadu Election AI Analytics Chatbot")
st.caption("Query election metrics, candidate statuses, rankings, and structural counts naturally.")

# Manage state-based memory cache for conversational interface
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display previous chat logs
for message in st.session_state.chat_history:
    with st.chat_message(message["identity"]):
        st.markdown(message["text"])
        if "data_view" in message:
            st.dataframe(message["data_view"])

# Capture user query
if prompt_input := st.chat_input("Ex: PERAMBUR votes counts for all participants?"):
    with st.chat_message("user"):
        st.markdown(prompt_input)
    st.session_state.chat_history.append({"identity": "user", "text": prompt_input})
    
    with st.chat_message("assistant"):
        # 1. Send request to Gemini
        with st.spinner("AI is compiling structural query logic..."):
            raw_llm_output = model.generate_content(f"{SYSTEM_CONTEXT}\n\nUser Question: {prompt_input}")
            raw_text = raw_llm_output.text.strip()
            
            # 🌟 STAGE 2: ADVANCED TEXT CLEANING GUARDRAILS
            # Clean out any common markdown structures if the AI provides them
            raw_text = raw_text.replace("```sql", "").replace("```", "").strip()
            
            # Find exactly where 'SELECT' starts to strip typos or prefixes like 'ite'
            if "SELECT" in raw_text:
                cleaned_sql = raw_text[raw_text.find("SELECT"):]
            else:
                cleaned_sql = raw_text

        # Display the execution logic to the user
        st.markdown("**Generated Execution Instructions:**")
        st.code(cleaned_sql, language="sql")
        
        # 3. Local Engine Database Query Execution
        with st.spinner("Computing database indices..."):
            cols, rows = execute_database_query(cleaned_sql)
            
        if cols is not None:
            if len(rows) > 0:
                structured_df = pd.DataFrame(rows, columns=cols)
                st.dataframe(structured_df)
                st.session_state.chat_history.append({
                    "identity": "assistant", 
                    "text": "Data fetched successfully:",
                    "data_view": structured_df
                })
            else:
                no_data_warning = "Query executed successfully, but returned 0 results. Please verify search name parameters."
                st.warning(no_data_warning)
                st.session_state.chat_history.append({"identity": "assistant", "text": no_data_warning})
        else:
            syntax_error_message = f"Syntax Compiler Error: {rows}"
            st.error(syntax_error_message)
            st.session_state.chat_history.append({"identity": "assistant", "text": syntax_error_message})