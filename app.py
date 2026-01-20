import streamlit as st 
import os
import atexit
from datetime import datetime
from dotenv import load_dotenv
import traceback

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

print("=" * 80)
print("[DEBUG] App.py started")
print(f"[DEBUG] Timestamp: {datetime.now().isoformat()}")
print("=" * 80)

# Page Configuration
st.set_page_config(
    page_title="Agentic Email AI", 
    page_icon="📧", 
    layout="wide"
)

print("[DEBUG] Page config set")

# Authentication Gate: 
# If authenticate_user() is False, it shows the login button and stops the app.
print("[DEBUG] Checking authentication...")
is_authenticated = authenticate_user()
print(f"[DEBUG] Authentication result: {is_authenticated}")

if not is_authenticated:
    print("[DEBUG] User not authenticated, showing login button")
    show_login_button()
    st.stop()

print("[DEBUG] User authenticated successfully!")

# Initialize Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
    print("[DEBUG] Initialized messages in session state")
    
if "graph_messages" not in st.session_state:
    st.session_state.graph_messages = []
    print("[DEBUG] Initialized graph_messages in session state")
    
if "thread_id" not in st.session_state:
    st.session_state.thread_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"[DEBUG] Created new thread_id: {st.session_state.thread_id}")

# ==============================================================================
# 2. DATABASE INTEGRATION (MONGODB)
# ==============================================================================

def get_mongo_collection():
    """Connect to MongoDB for session storage."""
    try:
        print("[DEBUG] Attempting MongoDB connection...")
        # Try environment variable first, then Streamlit secrets
        mongo_uri = os.getenv('MONGODB_URI')
        if not mongo_uri:
            try:
                mongo_uri = st.secrets["MONGODB_URI"]
            except (KeyError, FileNotFoundError):
                pass
        
        if not mongo_uri:
            print("[DEBUG] No MongoDB URI found, skipping database")
            return None
            
        print(f"[DEBUG] MongoDB URI found (first 20 chars): {mongo_uri[:20]}...")
        client = MongoClient(mongo_uri)
        collection = client['email_agent_db']['user_sessions']
        print("[DEBUG] MongoDB connected successfully")
        return collection
        
    except Exception as e:
        print(f"[ERROR] MongoDB connection failed: {e}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return None

collection = get_mongo_collection()

def save_chat_to_db():
    """Saves current session messages to MongoDB."""
    if collection is not None and st.session_state.graph_messages:
        try:
            print(f"[DEBUG] Saving chat to DB, message count: {len(st.session_state.graph_messages)}")
            
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
            print("[DEBUG] Chat saved to DB successfully")
            
        except Exception as e:
            print(f"[ERROR] Failed to save to DB: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

# Save session when the script terminates
atexit.register(save_chat_to_db)



# ==============================================================================
# 3. LANGGRAPH AGENT SETUP
# ==============================================================================

print("[DEBUG] Setting up LangGraph agent...")

try:
    # Initialize the LLM (Gemini 2.0)
    # Try environment variable first, then Streamlit secrets
    api_key = ""
    if not api_key:
        try:
            api_key = st.secrets['GEMINI_API_KEY']
            st.write(f"api key is {api_key}")
        except (KeyError, FileNotFoundError):
            st.error("API KEY NOT FOUND")
    
    if not api_key:
        print("[ERROR] No Gemini API key found!")
        st.error("❌ Gemini API key not configured. Please add GEMINI_API_KEY to your secrets.")
        st.stop()
    
    print(f"[DEBUG] Gemini API key found (first 10 chars): {api_key[:10]}...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=0.2, 
        api_key=api_key
    )
    print("[DEBUG] LLM initialized successfully")

    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(EMAIL_TOOLS)
    print(f"[DEBUG] Bound {len(EMAIL_TOOLS)} tools to LLM")

    # Define Agent State
    class AgentState(TypedDict):
        messages: Annotated[List[BaseMessage], operator.add]

    # Node: LLM Reasoner
    def agent_node(state: AgentState):
        print("[DEBUG] Agent node called")
        messages = state["messages"]
        print(f"[DEBUG] Message count in state: {len(messages)}")
        
        # Prepend System Prompt if this is a new conversation
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
            print("[DEBUG] Added system prompt to messages")
        
        try:
            response = llm_with_tools.invoke(messages)
            print(f"[DEBUG] LLM response received, type: {type(response)}")
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"[DEBUG] LLM wants to call {len(response.tool_calls)} tool(s)")
            return {"messages": [response]}
        except Exception as e:
            print(f"[ERROR] Agent node error: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            raise

    # Conditional Logic: Should we call a tool or end?
    def router(state: AgentState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            print("[DEBUG] Router: Routing to tools")
            return "tools"
        print("[DEBUG] Router: Routing to END")
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
    print("[DEBUG] LangGraph workflow compiled successfully")

except Exception as e:
    print(f"[ERROR] Failed to setup LangGraph agent: {e}")
    print(f"[ERROR] Traceback: {traceback.format_exc()}")
    st.error(f"❌ Failed to initialize agent: {e}")
    st.stop()

# ==============================================================================
# 4. STREAMLIT UI & INTERACTION
# ==============================================================================

st.title("📧 Agentic Email Assistant")
st.markdown("Your AI partner for managing Gmail inboxes, searching threads, and drafting replies.")

# Show authentication success
st.success("✅ Successfully authenticated and connected to Gmail!")

# Sidebar Controls
with st.sidebar:
    st.header("Settings")
    
    # Debug info expander
    with st.expander("🔍 Debug Info"):
        st.write(f"**Thread ID:** `{st.session_state.thread_id}`")
        st.write(f"**Messages:** {len(st.session_state.messages)}")
        st.write(f"**Graph Messages:** {len(st.session_state.graph_messages)}")
        st.write(f"**MongoDB:** {'✅ Connected' if collection else '❌ Not Connected'}")
        
        if 'gmail_service' in st.session_state:
            st.write("**Gmail Service:** ✅ Active")
        
        if 'credentials' in st.session_state:
            st.write("**OAuth Credentials:** ✅ Present")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        print("[DEBUG] Clear chat button pressed")
        st.session_state.messages = []
        st.session_state.graph_messages = []
        st.session_state.thread_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        print(f"[DEBUG] New thread_id: {st.session_state.thread_id}")
        st.rerun()
    
    if st.button("🚪 Logout", use_container_width=True):
        print("[DEBUG] Logout button pressed")
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    st.info("✅ System Status: Online")

# Display Chat History
print(f"[DEBUG] Displaying {len(st.session_state.messages)} messages")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask me to 'Check for unread emails from Amazon' or 'Summarize my last 5 emails'..."):
    
    print(f"[DEBUG] User input received: {prompt[:50]}...")
    
    # 1. Display User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.graph_messages.append(HumanMessage(content=prompt))
    print("[DEBUG] User message added to session state")

    # 2. Run Agent
    with st.chat_message("assistant"):
        with st.spinner("AI is accessing your inbox..."):
            try:
                print("[DEBUG] Invoking email_agent graph...")
                print(f"[DEBUG] Current graph_messages count: {len(st.session_state.graph_messages)}")
                
                # Execute the Graph
                result = email_agent.invoke({"messages": st.session_state.graph_messages})
                
                print(f"[DEBUG] Graph execution completed")
                print(f"[DEBUG] Result messages count: {len(result['messages'])}")
                
                # Get the latest message from the graph
                final_ai_msg = result["messages"][-1]
                response_text = final_ai_msg.content
                
                print(f"[DEBUG] Final AI response (first 100 chars): {response_text[:100]}...")
                
                # Update Session History
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # We update graph_messages with everything produced by the graph 
                # (includes intermediate ToolMessages so the agent remembers what it did)
                new_msgs = result["messages"][len(st.session_state.graph_messages):]
                st.session_state.graph_messages.extend(new_msgs)
                
                print(f"[DEBUG] Added {len(new_msgs)} new messages to graph_messages")
                print(f"[DEBUG] Total graph_messages: {len(st.session_state.graph_messages)}")

                # Render the final response
                st.markdown(response_text)
                
                # Save to database
                print("[DEBUG] Saving to database...")
                save_chat_to_db()
                print("[DEBUG] Request completed successfully")

            except Exception as e:
                error_msg = f"Error communicating with Agent: {str(e)}"
                print(f"[ERROR] {error_msg}")
                print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
                
                st.error(error_msg)
                
                with st.expander("🔍 View detailed error"):
                    st.code(traceback.format_exc())

print("[DEBUG] App.py execution completed")
print("=" * 80)