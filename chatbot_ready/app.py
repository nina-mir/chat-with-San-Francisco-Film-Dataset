import streamlit as st
from src.chatbot_coordinator import ChatbotCoordinator
from src.response_formatter import ResponseFormatter
import pandas as pd
import geopandas as gpd
import json

# Page config
st.set_page_config(
    page_title="SF Film Locations Chat",
    page_icon="🎬🌉🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ✨ BEAUTIFUL CUSTOM CSS
st.markdown("""
<style>
    /* Main chat container */
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
background: linear-gradient(90deg, hsla(291, 26%, 86%, 1) 0%, hsla(150, 36%, 85%, 1) 19%, hsla(339, 100%, 55%, 1) 56%, hsla(350, 5%, 51%, 1) 70%, hsla(105, 11%, 85%, 1) 100%);
        color: black;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
        color: black;
        font-weight: 200;
        text-shadow: -1px 1px gray;
    }
</style>
""", unsafe_allow_html=True)

# ✨ BEAUTIFUL HEADER
st.markdown("""
<div class="main-header">
    <h1>🎬 San Francisco Film Locations</h1>
    <p>Explore thousands of filming locations using natural language</p>
</div>
""", unsafe_allow_html=True)


def make_hashable(obj):
    """
    Convert unhashable types (lists, dicts with lists) to hashable types.
    This is needed for Streamlit's session_state which requires hashable objects.

    Args:
        obj: Any object that might contain unhashable types

    Returns:
        A hashable version of the object (or a JSON string for complex objects)
    """
    if obj is None:
        return None

    # If it's a DataFrame or GeoDataFrame, convert to JSON string
    if isinstance(obj, (pd.DataFrame, gpd.GeoDataFrame)):
        return obj.to_json()

    # If it's a dict, recursively convert values
    if isinstance(obj, dict):
        try:
            # Try to JSON serialize it - if it works, return JSON string
            return json.dumps(obj, default=str, sort_keys=True)
        except:
            # If serialization fails, convert each value individually
            return {k: make_hashable(v) for k, v in obj.items()}

    # If it's a list, convert to tuple (hashable)
    if isinstance(obj, list):
        return tuple(make_hashable(item) for item in obj)

    # If it's already hashable, return as-is
    try:
        hash(obj)
        return obj
    except TypeError:
        # Last resort: convert to string
        return str(obj)


# Initialize session state
def initialize_session_state():
    """Setup session variables on first run"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'coordinator' not in st.session_state:
        st.session_state.coordinator = ChatbotCoordinator()

    if 'formatter' not in st.session_state:
        st.session_state.formatter = ResponseFormatter()

    if 'last_result' not in st.session_state:
        st.session_state.last_result = None

# Main app function


def main():
    initialize_session_state()

    # Sidebar
    display_sidebar()

    # Create a container for chat history with max height
    chat_container = st.container()

    with chat_container:
        display_chat_history()

    # Input ALWAYS at bottom, outside containers
    handle_user_input()


def display_chat_history():
    """Render all previous messages"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Display additional components (maps, dataframes)
            if "map_html" in message:
                st.components.v1.html(message["map_html"], height=500)

            if "dataframe" in message:
                st.dataframe(message["dataframe"])


def handle_user_input():
    """Process new user messages"""
    user_input = None

    # Check if there's a pending query from sidebar button
    if 'pending_query' in st.session_state:
        user_input = st.session_state.pending_query
        # Clear it so it doesn't repeat
        del st.session_state.pending_query

    # Normal chat input
    chat_input = st.chat_input("Ask me about SF film locations...")

    # Use either the pending query or the chat input
    user_input = user_input or chat_input

    if user_input:
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(user_input)

        # Process and respond
        with st.chat_message("assistant"):
            with st.spinner("🔍 Processing your query..."):
                response = process_user_message(user_input)
                display_response(response)


def process_user_message(user_input: str):
    """Send message to coordinator and get response"""
    coordinator = st.session_state.coordinator
    formatter = st.session_state.formatter

    try:
        print(f"\n🔍 APP: Processing message: '{user_input}'")

        # Route message and get results
        result = coordinator.handle_message(
            user_input,
            context={'last_result': st.session_state.last_result}
        )

        print(f"🔍 APP: Got result from coordinator")
        print(f"🔍 APP: Result type: {result.get('type')}")
        print(f"🔍 APP: Result keys: {result.keys()}")

        # 🔧 FIX: Convert result to hashable before storing
        # Store a simplified/hashable version for session state
        st.session_state.last_result = make_hashable(result)

        # Format for display
        print(f"🔍 APP: Calling formatter.format_response()")
        formatted_response = formatter.format_response(result)

        print(f"🔍 APP: Got formatted response")
        print(f"🔍 APP: Formatted keys: {formatted_response.keys()}")

        return formatted_response

    except Exception as e:
        print(f"\n❌ APP ERROR: {e}")
        import traceback
        traceback.print_exc()

        return {
            'content': f"⚠️ Oops! Something went wrong: {str(e)}",
            'type': 'error'
        }


def prepare_geodataframe_for_display(df):
    """
    Prepare a GeoDataFrame for Streamlit display by converting geometry to WKT.

    Args:
        df: DataFrame or GeoDataFrame to prepare

    Returns:
        Regular DataFrame with geometry as string (if it was a GeoDataFrame)
    """
    if not isinstance(df, gpd.GeoDataFrame):
        return df

    display_df = df.copy()

    # Convert geometry column to WKT string
    if 'geometry' in display_df.columns:
        display_df['geometry'] = display_df['geometry'].apply(
            lambda geom: geom.wkt if geom is not None else None
        )

    # Convert to regular DataFrame to avoid any GeoDataFrame-specific issues
    return pd.DataFrame(display_df)


def display_response(response):
    """Display formatted response"""
    # Display text content
    st.markdown(response['content'])
    print('response is :', response)
    # Display dataframe if present
    if 'dataframe' in response:
        df = response['dataframe']

        # Convert GeoDataFrame to regular DataFrame for display
        display_df = prepare_geodataframe_for_display(df)

        # Show dataframe
        if len(display_df) > 20:
            with st.expander(f"📊 View All {len(display_df)} Results", expanded=False):
                st.dataframe(display_df, use_container_width=True)
        else:
            st.dataframe(display_df, use_container_width=True)

        # 🔧 FIX: Use a simpler unique key that doesn't hash the dataframe
        import time
        unique_key = f"download_{len(display_df)}_{int(time.time() * 1000000)}"

        # Add download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv",
            key=unique_key
        )

    # Display map if present
    if 'map_html' in response:
        st.components.v1.html(response['map_html'], height=500)

    # 🔧 FIX: Store a hashable version of the response
    # Store only the essential parts, not complex objects
    message_to_store = {
        "role": "assistant",
        "content": response['content']
    }

    # Only add dataframe and map_html if present (but store them as-is, not as hashable)
    # Streamlit can handle these specific types
    if 'dataframe' in response:
        message_to_store['dataframe'] = response['dataframe']
    if 'map_html' in response:
        message_to_store['map_html'] = response['map_html']

    st.session_state.messages.append(message_to_store)


def display_sidebar():
    """Enhanced sidebar with examples and stats"""
    # Create a clickable GitHub logo in sidebar
    github_logo_html = """
    <a href="https://github.com/nina-mir/DigitalOcean-hackathon-FILM-2025" target="_blank">
        <img src="/github-mark/github-mark-white.svg" alt="GitHub" width="30" style="vertical-align:middle;margin-bottom:5px;"/>
    </a>
    """

    github_logo_html = """
    <a style="text-decoration:none; display:flex;justify-content:center; gap:1rem;"
    href="https://github.com/nina-mir/DigitalOcean-hackathon-FILM-2025" target="_blank">
    <img src="https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/github.svg" 
         alt="GitHub" width="30" style="vertical-align:middle;margin-bottom:5px;"/>
    <span style="background-color:pink;padding:0.2rem;border-radius: 15px;">View on GitHub</span>
</a>
"""

    with st.sidebar:
        # st.sidebar.image("./github-mark/github-mark.png", caption="GitHub", width=30) 
        st.sidebar.markdown(github_logo_html, unsafe_allow_html=True)
        # st.markdown(
        # "[⭐ View on GitHub](https://github.com/nina-mir/DigitalOcean-hackathon-FILM-2025)",
        # unsafe_allow_html=True
        # )

         # HELP SECTION
        with st.expander("ℹ️ How to Use"):
            st.markdown("""
            **Ask questions like:**
            - "Films shot at [location]"
            - "All [director] movies"
            - "Which actor appeared most?"
            - "How many movies from [year]?"
            
            **Features:**
            - 🗺️ Interactive maps
            - 📊 Downloadable data tables
            - 💬 Natural language queries
            """)


        st.markdown("### 🎯 Quick Start")

        example_queries = [
            ("🌉", "What films were shot at the Golden Gate Bridge?"),
            ("📍", "Find all movies shot within 0.5 mile radius of the Union Square. List the film names and the specific location."),
            ("🎭", "Show me all Hitchcock filming locations"),
            ("🎭", "Any films made in 1910s in SF?"),
            ("📅", "How many movies from the 1970s?"),
            ("⭐", "Which actor appeared in the most films?"),
            ("🎬", "Films with 'matrix' in the title")
        ]

        for idx, (emoji, query) in enumerate(example_queries):
            # 🔧 FIX: Use index instead of hash for button keys
            if st.button(
                f"{emoji} {query}",
                key=f"example_{idx}",  # Simple index-based key
                use_container_width=True
            ):
                st.session_state.pending_query = query
                st.rerun()

        st.markdown("---")

        # 📈 DATABASE STATS - COOL!
        st.markdown("### 📈 Database Stats")
        try:
            gdf = st.session_state.coordinator.query_processor.gdf

            col1, col2 = st.columns(2)
            with col1:
                st.metric("📍 Locations", f"{len(gdf):,}")
                unique_films = gdf[['Title', 'Year']].drop_duplicates()
                st.metric("🎬 Films", f"{len(unique_films):,}")

            with col2:
                unique_actors = pd.concat([
                    gdf['Actor_1'], gdf['Actor_2'], gdf['Actor_3']
                ]).dropna().nunique()
                st.metric("⭐ Actors", f"{unique_actors:,}")

                years = pd.to_numeric(gdf['Year'], errors='coerce').dropna()
                if len(years) > 0:
                    st.metric(
                        "📅 Years", f"{int(years.min())}-{int(years.max())}")
        except Exception as e:
            st.info("Stats loading...")
       
        # RESET BUTTON
        st.markdown("---")
        if st.button("🔄 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_result = None
            st.success("Chat cleared!")
            st.rerun()


if __name__ == "__main__":
    main()
