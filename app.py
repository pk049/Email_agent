import streamlit as st 
import os
import atexit
from datetime import datetime
from dotenv import load_dotenv

# Database & LangChain imports
from pymongo import MongoClient
from typing import TypedDict, Annotated, List, Dict
import operator
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# Custom imports
from Operations.email_operations import LANGCHAIN_TOOLS as EMAIL_TOOLS
from system_prompt import SYSTEM_PROMPT
from auth import authenticate_user, show_login_button

# Load environment variables (for local development)
load_dotenv()

# ==============================================================================
# 1. INITIALIZATION & AUTHENTICATION GATE
# ==============================================================================

# Page Configuration
st.set_page_config(
    page_title="Agentic Email AI", 
    page_icon="📧", 
    layout="wide"
)

# Authentication Gate: 
# If authenticate_user() is False, it shows the login button and stops the app.
if not authenticate_user():
    show_login_button()
    st.stop()

# Initialize Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph_messages" not in st.session_state:
    st.session_state.graph_messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = datetime.now().strftime('%Y%m%d_%H%M%S')

# ==============================================================================
# 2. DATABASE INTEGRATION (MONGODB)
# ==============================================================================

def get_mongo_collection():
    """Connect to MongoDB for session storage."""
    try:
        mongo_uri = os.getenv('MONGODB_URI') or st.secrets.get("MONGODB_URI")
        if mongo_uri:
            client = MongoClient(mongo_uri)
            return client['email_agent_db']['user_sessions']
        return None
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return None

collection = get_mongo_collection()

def save_chat_to_db():
    """Saves current session messages to MongoDB."""
    if collection is not None and st.session_state.graph_messages:
        try:
            # Prepare message history for DB storage
            history = []
            for msg in st.session_state.graph_messages:
                history.append({
                    "role": msg.type,
                    "content": msg.content,
                    "timestamp": datetime.now().isoformat()
                })

            session_record = {
                "session_id": st.session_state.thread_id,
                "updated_at": datetime.now().isoformat(),
                "history": history
            }
            collection.replace_one(
                {"session_id": st.session_state.thread_id}, 
                session_record, 
                upsert=True
            )
        except Exception as e:
            print(f"Failed to save to DB: {e}")

# Save session when the script terminates
atexit.register(save_chat_to_db)

# ==============================================================================
# 3. LANGGRAPH AGENT SETUP
# ==============================================================================

# Initialize the LLM (Gemini 2.0)
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp", 
    temperature=0.2, 
    api_key=api_key
)

# Bind tools to the LLM
llm_with_tools = llm.bind_tools(EMAIL_TOOLS)

# Define Agent State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]

# Node: LLM Reasoner
def agent_node(state: AgentState):
    messages = state["messages"]
    # Prepend System Prompt if this is a new conversation
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# Conditional Logic: Should we call a tool or end?
def router(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# Build the Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(EMAIL_TOOLS))

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", router)
workflow.add_edge("tools", "agent")

# Compile the Graph
email_agent = workflow.compile()

# ==============================================================================
# 4. STREAMLIT UI & INTERACTION
# ==============================================================================

st.title("📧 Agentic Email Assistant")
st.markdown("Your AI partner for managing Gmail inboxes, searching threads, and drafting replies.")

# Sidebar Controls
with st.sidebar:
    st.header("Settings")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.graph_messages = []
        st.session_state.thread_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        st.rerun()
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    st.info("System Status: Online")

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask me to 'Check for unread emails from Amazon' or 'Summarize my last 5 emails'..."):
    
    # 1. Display User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.graph_messages.append(HumanMessage(content=prompt))

    # 2. Run Agent
    with st.chat_message("assistant"):
        with st.spinner("AI is accessing your inbox..."):
            try:
                # Execute the Graph
                result = email_agent.invoke({"messages": st.session_state.graph_messages})
                
                # Get the latest message from the graph
                final_ai_msg = result["messages"][-1]
                response_text = final_ai_msg.content
                
                # Update Session History
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # We update graph_messages with everything produced by the graph 
                # (includes intermediate ToolMessages so the agent remembers what it did)
                new_msgs = result["messages"][len(st.session_state.graph_messages):]
                st.session_state.graph_messages.extend(new_msgs)

                # Render the final response
                st.markdown(response_text)
                
                # Save to database
                save_chat_to_db()

            except Exception as e:
                st.error(f"Error communicating with Agent: {str(e)}")