import os
import shutil
import pandas as pd

from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

DATA_DIR = "data"
DB_DIR = "vector_db"


def load_documents():
    documents = []

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    for file in os.listdir(DATA_DIR):
        path = os.path.join(DATA_DIR, file)

        if file.endswith(".txt"):
            loader = TextLoader(path, encoding="utf-8")
            documents.extend(loader.load())

        elif file.endswith(".pdf"):
            loader = PyPDFLoader(path)
            documents.extend(loader.load())

        elif file.endswith(".csv"):
            df = pd.read_csv(path)

            for _, row in df.iterrows():
                content = " | ".join(
                    [f"{col}: {row[col]}" for col in df.columns]
                )

                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": file,
                            "route_id": str(row.get("route_id", "unknown")),
                            "from_city": str(row.get("from_city", "")),
                            "to_city": str(row.get("to_city", "")),
                            "provider": str(row.get("provider", "")),
                            "date": str(row.get("date", ""))
                        }
                    )
                )

    return documents


def build_vector_db():
    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)

    documents = load_documents()

    if not documents:
        print("No files found in data folder.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_DIR
    )

    print("Vector DB created successfully with CSV data!")


if __name__ == "__main__":
    build_vector_db()