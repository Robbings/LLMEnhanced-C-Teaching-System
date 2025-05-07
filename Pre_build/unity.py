import getpass
import os
from logging import Logger

from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

llm = init_chat_model("deepseek-v3", model_provider="openai")
embeddings = DashScopeEmbeddings(
    model="text-embedding-v2",
    dashscope_api_key=os.getenv("OPENAI_API_KEY"),
)

vector_store = Chroma(
    collection_name="unity_documents",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",  # Where to save data locally, remove if not necessary
)

directory = ".\\unity_documents"
files = []
for filename in os.listdir(directory):
    if filename.endswith(".md"):
        files.append(os.path.join(directory, filename))

for file in files:
    Logger.info(f"Processing file: {file}")
    loader = TextLoader(file, encoding = 'UTF-8')
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_splits = text_splitter.split_documents(docs)
    _ = vector_store.add_documents(documents=all_splits)
Logger.info("All documents have been added to the vector store.")

