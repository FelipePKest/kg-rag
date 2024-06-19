from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain.prompts.chat import (ChatPromptTemplate)
from langchain_core.documents import Document
from langchain_community.document_loaders import SeleniumURLLoader
# from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_community.graphs import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from dotenv import load_dotenv

import os
import json

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

host = os.environ.get('NEO4J_AURA_URL')
user = os.environ.get('NEO4J_AURA_USER')
password = os.environ.get('NEO4J_AURA_PASS')

graph = Neo4jGraph(url=host, username=user, password=password)
# print(host, user, password)


llm = ChatOllama(model="llama3", temperature=0, top_k=1)
llm = ChatOpenAI(api_key=OPENAI_API_KEY,temperature=0, model_name="gpt-3.5-turbo")
llm_transformer = LLMGraphTransformer(llm=llm)


# Convert text to graph
def convert_to_graph(file, llm_transformer=llm_transformer, graph=graph):
    text = file["content"]
    source = file["metadata"]["source"]
    documents = [Document(page_content=text, metadata={"source": source})]
    graph_documents = llm_transformer.convert_to_graph_documents(documents)
    graph.add_graph_documents(graph_documents, include_source=True)
    return graph_documents

file = open('evaluation/aux_files/news_content1.json', encoding='utf-8')
json_file = json.load(file)
i = 0
for item in json_file[:500]:
    # print(item["content"])
    try:
        graph_docs = convert_to_graph(item)
    except Exception as e:
        print("Error: ", e)
    print("At index: ", i)
    i += 1
    # print(graph_docs)
file.close()
graph._driver.close()