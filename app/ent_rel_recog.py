from langchain_openai import ChatOpenAI
from langchain.prompts.chat import (ChatPromptTemplate)
from langchain_core.documents import Document
from langchain_community.document_loaders import SeleniumURLLoader
# from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_community.graphs import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from dotenv import load_dotenv

import os

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

host = os.environ.get('NEO4J_AURA_URL')
user = os.environ.get('NEO4J_AURA_USER')
password = os.environ.get('NEO4J_AURA_PASS')

# print(host, user, password)

llm = ChatOpenAI(api_key=OPENAI_API_KEY,temperature=0, model_name="gpt-3.5-turbo")
llm_transformer = LLMGraphTransformer(llm=llm)

urls = [
    "https://ge.globo.com/futebol/times/corinthians/noticia/2024/02/16/corinthians-anuncia-a-contratacao-do-lateral-direito-matheuzinho.ghtml",
    "https://ge.globo.com/futebol/times/botafogo/noticia/2024/02/16/luiz-henrique-do-botafogo-tem-lesao-na-panturrilha.ghtml",
    "https://ge.globo.com/futebol/times/fluminense/noticia/2024/02/16/escalacao-do-fluminense-diniz-escala-reservas-contra-madureira-mas-tera-john-kennedy-e-douglas-costa.ghtml",
]

# loader = SeleniumURLLoader(urls=urls)
# docs = loader.load()

# Convert text to graph
def convert_to_graph(text):
    documents = [Document(page_content=text)]
    graph_documents = llm_transformer.convert_to_graph_documents(documents)
    graph = Neo4jGraph(url=host, username=user, password=password)
    graph.add_graph_documents(graph_documents)
    return graph_documents

def url_to_graph(urls):
    loader = SeleniumURLLoader(urls=urls)
    docs = loader.load()
    graph_documents = llm_transformer.convert_to_graph_documents(docs)
    graph = Neo4jGraph(url=host, username=user, password=password)
    graph.add_graph_documents(graph_documents)
    return graph_documents

# for doc in docs:
#     print(doc.page_content)
#     print(convert_to_graph(doc.page_content))

