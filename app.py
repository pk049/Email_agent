# =========================================================================================================
#                        PHASE 0 : LOADING LIBRARIES AND CREATING HELPER UTILS(Agentstate,Mongodb)
# ==========================================================================================================
import streamlit as st 
import time
import os
import atexit

from pymongo import MongoClient
from typing import TypedDict,Annotated,List
import operator


from langchain_core.messages import BaseMessage,AIMessage,HumanMessage,ToolMessage,SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from Operations.email_operations import LANGCHAIN_TOOLS as EMAIL_TOOLS

from system_prompt import SYSTEM_PROMPT

from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ===================================
#   STREAMLIT STATE CREATION
# ==================================
if "messages" not in st.session_state:
    st.session_state.messages=[]
if "graph_messages" not in st.session_state:
    st.session_state.graph_messages=[]


#======================
# TOOL NAMES EXTRACTION
# =====================
ALL_TOOLS=EMAIL_TOOLS


# ======================
#   CONNECT TO MONGOD
# ======================
try:
  mongo_uri=os.getenv('MONGODB_URI',"mongodb://localhost:27017")
  
  conn = MongoClient(mongo_uri)
  db = conn['newdb']
  collection = db['tds']
  info = conn.server_info()
  
  print("✅ Connected successfully To Mongo ..")
  
except Exception as e:
  print(f"❌ MongoDB connection failed: {e}")
  collection = None


# ==================================
# SAVE FINAL SESSION TO MONGODB
# ==================================
def save_final_session(thread_id: str, session_start: str):
    """Save complete final session with session_end timestamp"""
    if collection is None:
        return
    
    try:
        session_end = datetime.now().isoformat()
        
        # Get all messages from session state
        all_messages = st.session_state.graph_messages
        
        conversation_history = []
        user_inputs = []
        
        for msg in all_messages:
            msg_data = {
                "type": msg.type,
                "content": msg.content,
                "timestamp": datetime.now().isoformat()
            }
            
            if isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    msg_data["tool_calls"] = [
                        {"name": tc.get("name"), "args": tc.get("args"), "id": tc.get("id")}
                        for tc in msg.tool_calls
                    ]
            elif isinstance(msg, ToolMessage):
                msg_data["tool_name"] = msg.name
                msg_data["tool_call_id"] = msg.tool_call_id
            elif isinstance(msg, HumanMessage):
                user_inputs.append(msg.content)
                
            conversation_history.append(msg_data)
        
        session_document = {
            "session_id": thread_id,
            "session_start": session_start,
            "session_end": session_end,
            "total_messages": len(all_messages),
            "user_inputs": user_inputs,
            "conversation_history": conversation_history,
            "session_duration": str(datetime.fromisoformat(session_end) - 
                                    datetime.fromisoformat(session_start)),
            "status": "completed"
        }
        
        # Use replace_one to completely replace the document
        result = collection.replace_one(
            {"session_id": thread_id},
            session_document,
            upsert=True
        )
        
        print(f"\n✅ Final session saved to MongoDB")
        print(f"📊 Session Stats:")
        print(f"   - Total messages: {len(all_messages)}")
        print(f"   - User inputs: {len(user_inputs)}")
        print(f"   - Duration: {session_document['session_duration']}")
        
        return True
    except Exception as e:
        print(f"\n⚠️ Failed to save final session: {e}")
        return False

              
              
# ======================
#   AGENT STATE
# =======================
class Agent_State(TypedDict):
    messages:Annotated[List[BaseMessage],operator.add]
    











# ========================================================================================================
#                                     PHASE 1 : MAKING THE GRAPH
# ========================================================================================================


# ===================================
# CREATING NODE FUNCTIONS OF GRAPHS
# ===================================
api_key=os.getenv("GEMINI_API_KEY")
llm=ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
llm=llm.bind_tools(ALL_TOOLS)
system_prompt = SYSTEM_PROMPT


# NODE 1 FUNCTION  
def llm_node(state: Agent_State):
    messages = state["messages"]

    try:
        # Add system message once at the beginning
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            messages = [SystemMessage(content=system_prompt)] + messages

        response = llm.invoke(messages)

        return {"messages": [response]}

    except Exception as e:
        return {"messages": [AIMessage(content=f"❌ LLM failed: {e}")]}

# NODE 2 IS TOOL NODE


# CONDITIONAL EDGE 
def should_continue(state: Agent_State):
    """Determines whether to continue with tools or end"""
    messages = state["messages"]
    last_msg = messages[-1]
    
    if isinstance(last_msg, AIMessage) and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return "tool_node"
    else:
        return END
     




# =========================
#    COMPILING GRAPH
# ======================
# CREATING GRAPH 
graph=StateGraph(Agent_State)

#add node 
graph.add_node("llm_node",llm_node)
graph.add_node("tool_node",ToolNode(ALL_TOOLS))

# add edges
graph.add_edge(START,"llm_node")
graph.add_conditional_edges("llm_node",should_continue)
graph.add_edge("tool_node","llm_node")

# compile WITHOUT checkpointer (we'll manage state manually)
graph=graph.compile()










# Display all messages on every rerun
def display_messages():
    for msg in st.session_state.messages:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])




# ================================================================================================================
#                                         PHASE 2 : RUNNNIG THE GRAPH
# ================================================================================================================ 


# =========================================
# INTERACTIVE MODE WITH PERSISTENT MEMORY 
# =========================================
def interactive_mode():
    """Run the agent in interactive mode with persistent conversation thread"""
    
    st.set_page_config(page_title="Multi-Agent System", page_icon="🤖", layout="wide")
    
    st.title("🤖 Multi-Agent System")
    st.caption("File & Email Operations with Persistent Memory")

    # Sidebar with info
    with st.sidebar:
        st.header("ℹ️ Information")
        st.write("**Available Operations:**")
        st.write("- 📧 Email operations")
        st.write("- 📁 File operations")
        st.write("- 💬 Natural conversation")
        
        if 'thread_id' in st.session_state:
            st.divider()
            st.write(f"**Session ID:** `{st.session_state.thread_id}`")
            st.write(f"**Messages:** {len(st.session_state.messages)}")
            st.write(f"**Graph Messages:** {len(st.session_state.graph_messages)}")
        
        st.divider()
        if st.button("🗑️ Clear Chat & Save Session", type="primary"):
            # Save before clearing
            if 'thread_id' in st.session_state:
                try:
                    save_final_session(
                        st.session_state.thread_id,
                        st.session_state.session_start
                    )
                    st.success("✅ Session saved to MongoDB!")
                    time.sleep(1)
                except Exception as e:
                    st.error(f"Error saving: {e}")
            
            st.session_state.clear()
            st.rerun()
    
    # create thread id and set configurations
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        st.session_state.session_start = datetime.now().isoformat()
        print(f"\n{'='*60}")
        print(f"🆕 New Session Started: {st.session_state.thread_id}")
        print(f"{'='*60}\n")
    
    thread_id = st.session_state.thread_id
    session_start = st.session_state.session_start
    
    # Display existing messages
    display_messages()
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        user_input = user_input.strip()
        
        print(f"\n{'='*60}")
        print(f"👤 User: {user_input}")
        print(f"{'='*60}")
        
        # Add user message to session state and display
        st.session_state.messages.append({'role': 'user', 'content': user_input})
        
        with st.chat_message('user'):
            st.markdown(user_input)
        
        # Show processing indicator
        with st.chat_message('assistant'):
            with st.spinner('Thinking...'):
                try:
                    # Create HumanMessage and add to graph messages
                    human_msg = HumanMessage(content=user_input)
                    st.session_state.graph_messages.append(human_msg)
                    
                    # Invoke graph with ALL accumulated messages
                    result = graph.invoke(
                        {"messages": st.session_state.graph_messages}
                    )
                    
                    if result and "messages" in result:
                        # Get all new messages from this interaction
                        new_messages = result["messages"][len(st.session_state.graph_messages):]
                        
                        # Add all new messages to graph_messages (including tool calls)
                        st.session_state.graph_messages.extend(new_messages)
                        
                        # Find the LAST AI message that has actual content (not just tool calls)
                        final_ai_message = None
                        for msg in reversed(new_messages):
                            if isinstance(msg, AIMessage):
                                # Skip AI messages that only have tool_calls but no content
                                if msg.content and msg.content.strip():
                                    final_ai_message = msg
                                    break
                        
                        if final_ai_message:
                            response_content = final_ai_message.content
                            
                            # Add to UI session state (only the final response)
                            st.session_state.messages.append({
                                'role': 'assistant',
                                'content': response_content
                            })
                            
                            # Display response
                            st.markdown(response_content)
                            
                            print(f"\n🤖 Assistant: {response_content}")
                            print(f"\n📊 Current state: {len(st.session_state.graph_messages)} messages in graph")
                        else:
                            # Fallback if no AI message found
                            error_msg = "⚠️ No response generated"
                            st.session_state.messages.append({
                                'role': 'assistant',
                                'content': error_msg
                            })
                            st.warning(error_msg)
                            
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.session_state.messages.append({'role': 'assistant', 'content': error_msg})
                    st.error(error_msg)
                    print(f"\n❌ Error: {e}")
        
        # Rerun to update the chat
        st.rerun()


# Register cleanup function to save on script termination
def cleanup():
    if collection is not None and 'thread_id' in st.session_state:
        try:
            save_final_session(
                st.session_state.thread_id,
                st.session_state.session_start
            )
            print("✅ Session saved on cleanup")
        except Exception as e:
            print(f"⚠️ Cleanup save failed: {e}")

atexit.register(cleanup)


if __name__ == '__main__':
    interactive_mode()