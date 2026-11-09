import streamlit as st
import requests 

# Page configuration
st.set_page_config(page_title="Chat with PDF", page_icon="")
st.title("Chat with PDF")
st.markdown("Ask questions about the document you ingested.")

#Initialize chat history in session state 
if "messages" not in st.session_state:
    st.session_state.messages = []


# Display previous chat message
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# The chat Input Box
if prompt := st.chat_input("Ask a question about the book..."):
    # Add user questions to chat history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send the question to your FastAPI backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post("http://host.docker.internal:8000/chat", json={"question": prompt})
                
                response_data = response.json()

                if response.status_code == 200:
                    answer = response_data["answer"]
                    sources = response_data["sources"]

                    st.markdown(answer)

                    with st.expander("View Sources"):
                        for i, sources in enumerate(sources):
                            st.write(f"**Source {i+1}:**")
                            st.info(sources)

                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error(f"Error: {response_data.get('detail')}")

            except Exception as e:
                st.error(f"Failed to connect to the backend. Is uvicorn running? Error: {e}")



