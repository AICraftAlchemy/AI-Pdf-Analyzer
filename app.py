import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from googlesearch import search
from googleapiclient.discovery import build
from requests.exceptions import HTTPError
import time

load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks


def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    # Create FAISS index temporarily in memory
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    return vector_store


def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not in
    provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """

    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)

    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)

    return chain


def user_input(user_question, vector_store, questions_answers):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    docs = vector_store.similarity_search(user_question)

    chain = get_conversational_chain()

    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)

    questions_answers.append((user_question, response["output_text"]))

    return response["output_text"]


def get_google_links(question):
    try:
        links = search(question, num_results=5)
        return list(links)
    except HTTPError as e:
        st.warning("Error occurred while fetching Google links. Skipping...")
        st.warning(e)
        return []


def get_youtube_links(question):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        search_response = youtube.search().list(q=question, part='id,snippet', maxResults=5).execute()
        youtube_links = []
        for item in search_response['items']:
            if item['id']['kind'] == 'youtube#video':
                youtube_links.append(f"https://www.youtube.com/watch?v={item['id']['videoId']}")
        return youtube_links
    except Exception as e:
        st.warning("Error occurred while fetching YouTube links. Skipping...")
        st.warning(e)
        return []


def main():
    st.set_page_config(page_title="Chat PDF", layout="wide")

    # Hide other elements
    hide_streamlit_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: visible;}
                header {visibility: hidden;}
                .stTextInput>div>div>textarea {min-height: 100px;}
                .stButton>button {background-color: #007BFF;}
                .stButton>button:hover {background-color: #0056b3;}
                .reportview-container .main .block-container{max-width: 100%;}
                </style>
                """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    # Dark/Light Mode Toggle
    theme = st.radio("Choose your theme", ["Light Mode", "Dark Mode"])

    if theme == "Dark Mode":
        st.markdown(
            """
            <style>
            body {background-color: #0e1117; color: #fafafa;}
            .stTextInput input {background-color: #1e1e1e; color: white;}
            .stButton>button {background-color: #fafafa; color: #0e1117;}
            </style>
            """, 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <style>
            body {background-color: white; color: black;}
            .stTextInput input {background-color: white; color: black;}
            .stButton>button {background-color: black; color: white;}
            </style>
            """, 
            unsafe_allow_html=True
        )

    st.title(":books: AI PDF ANALYZER")

    # Display image with reduced size
    st.image("src/image.jpg", width=300)

    st.markdown(
        "This AI PDF ANALYZER provides answers **exclusively from the uploaded PDF files** and external sources (Google and YouTube) for better insights."
    )

    # Upload PDF files
    pdf_docs = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button",
                                 accept_multiple_files=True)
    if st.button("Submit & Process"):
        with st.spinner("Processing..."):
            raw_text = get_pdf_text(pdf_docs)
            text_chunks = get_text_chunks(raw_text)
            # Temporarily store the FAISS index in memory
            st.session_state.vector_store = get_vector_store(text_chunks)
            st.success("Done")

    user_question = st.text_input("Ask a Question from the PDF Files", key="user_input")

    if st.button("Submit Question"):
        if "questions_answers" not in st.session_state:
            st.session_state.questions_answers = []
        if user_question and "vector_store" in st.session_state:
            st.write("Generating answer...")
            with st.spinner("Processing..."):
                time.sleep(1)
                st.write("Thinking...")
                time.sleep(1)
                st.write("Almost there...")
                time.sleep(1)
                answer = user_input(user_question, st.session_state.vector_store, st.session_state.questions_answers)
                google_links = get_google_links(user_question)
                youtube_links = get_youtube_links(user_question)
                st.write("Reply: ", answer)
                st.write("Google Links:")
                for link in google_links:
                    st.write(link)
                st.write("YouTube Links:")
                for link in youtube_links:
                    st.write(link)
                if len(st.session_state.questions_answers) >= 2:
                    st.markdown("## Previous Questions and Answers")
                    for question, answer in reversed(st.session_state.questions_answers[:-1]):
                        st.write("**Question:**", question)
                        st.write("**Answer:**", answer)
                        st.write("**Google Links:**")
                        links = get_google_links(question)
                        for link in links:
                            st.write(link)
                        st.write("**YouTube Links:**")
                        links = get_youtube_links(question)
                        for link in links:
                            st.write(link)
                        st.write("---")

    st.markdown(
        """
        ---
        ### For any queries, reach me at:
        - **Email**: aicraftalchemy@gmail.com
        - **Phone**: +917661081043
        """
    )


if __name__ == "__main__":
    main()
