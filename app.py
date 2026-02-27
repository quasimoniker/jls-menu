import streamlit as st
from offmenu.retriever import ask, find_episode_filter
from offmenu.router import get_route
from offmenu.csv_answerer import answer_from_csv

st.set_page_config(page_title="Off Menu Chatbot", page_icon="🍽️")

st.title("🍽️ Off Menu Chatbot")
st.markdown("Ask anything about the Off Menu podcast with Ed Gamble and James Acaster.")

# keep chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# chat input
if prompt := st.chat_input("Ask a question about Off Menu..."):
    # show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # get and show response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            route = get_route(prompt)
            if route == "csv":
                st.caption("Searching menu choices data")
                response = answer_from_csv(prompt)
            else:
                episode_filter = find_episode_filter(prompt)
                if episode_filter:
                    st.caption(f"Searching episode {episode_filter}")
                response = ask(prompt)
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})