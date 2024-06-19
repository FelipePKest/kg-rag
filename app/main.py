import os
import streamlit as st
from streamlit_chat import message

import networkx as nx
from neo4j import GraphDatabase
from response_handlers import generate_entity_query_context, generate_response, graph_from_query
# from response_handlers.response2text import generate_response
# from response_handlers.response2networkx import graph_from_query, generate_entity_query_context
from graph_schema_viz import movies_gds_db, gds_db
from ent_rel_recog import convert_to_graph, url_to_graph 
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(layout="wide")
st.set_option('deprecation.showPyplotGlobalUse', False)
st.title("Usando LLM's para consultas em grafos de conhecimento")

# WARNING: This will PERMANENTLY delete the entire database
# if ONLY_NEW_CONTENT:
if st.button("Delete database"):
    host = os.environ.get('NEO4J_AURA_URL')
    user = os.environ.get('NEO4J_AURA_USER')
    password = os.environ.get('NEO4J_AURA_PASS')
    driver = GraphDatabase.driver(host, auth=(user, password))
    # st.stop()
    # gds_db.run('''CALL apoc.periodic.iterate("MATCH (n) RETURN n","DETACH DELETE n", {batchSize:10, parallel:false})''')
    print("Deleting previous database content")

query_mode = st.checkbox("QUERY MODE", True)

data_source = st.selectbox(
    'Source of data:',
    ('Movies Database','Simple text', 'URL'))

def generate_context(prompt, context_data='generated'):
    context = []
    # If any history exists
    if st.session_state['generated']:
        # Add the last three exchanges
        EXCHANGE_LIMIT = 3
        size = len(st.session_state['generated'])
        for i in range(max(size-EXCHANGE_LIMIT, 0), size):
            context.append(
                {'role': 'user', 'content': st.session_state['user_input'][i]})
            context.append(
                {'role': 'assistant', 'content': st.session_state[context_data][i]})
    # Add the latest user prompt
    context.append({'role': 'user', 'content': str(prompt)})
    return context


# Generated natural language
if 'generated' not in st.session_state:
    st.session_state['generated'] = []
# Neo4j database results
if 'database_results' not in st.session_state:
    st.session_state['database_results'] = []
# User input
if 'user_input' not in st.session_state:
    st.session_state['user_input'] = []
# Generated Cypher statements
if 'cypher' not in st.session_state:
    st.session_state['cypher'] = []
# Graph    
if 'graph' not in st.session_state:
    st.session_state['graph'] = []

def get_text():
    input_text = st.text_input(
        "Ask away", "", key="input")
    return input_text


# Define columns
col1, col2 = st.columns([2, 1])

with col2:
    another_placeholder = st.empty()
    third_placeholder = st.empty()
with col1:
    placeholder = st.empty()
user_input = get_text()


if user_input:
    if data_source == 'Movies Database':
        # webpage = st.toggle("Load url", False)
        # Hardcoded UserID
        USER_ID = "Tomaz"

        # On the first execution, we have to create a user node in the database.
        movies_gds_db.query_database("""MERGE (u:User {id: $userId})""", {'userId': USER_ID})

        # cypher = generate_cypher(generate_context(user_input, 'database_results'))
        cypher = movies_gds_db.construct_cypher(user_input)
        # If not a valid Cypher statement
        if not "MATCH" in cypher:
            print('No Cypher was returned')
            st.session_state.user_input.append(user_input)
            st.session_state.generated.append(
                cypher)
            st.session_state.cypher.append(
                "No Cypher statement was generated")
            st.session_state.database_results.append("")
        else:
            # results = run_query(cypher, {'userId': USER_ID})
            results = movies_gds_db.run(user_input)
            # Harcode result limit to 10
            results = results[:10]
            
            # Graph2text
            answer = generate_response(generate_context(
                f"Question was {user_input} and the response should include only information that is given here: {str(results)}"))

            entity_cypher = movies_gds_db.construct_full_entity_cypher(user_input)
            # Graph figure
            G, labels = graph_from_query(entity_cypher, movies_gds_db.driver, test_db=True)

            st.session_state.database_results.append(str(results))
            st.session_state.graph.append(str(results))
            st.session_state.user_input.append(user_input)
            st.session_state.generated.append(answer)
            st.session_state.cypher.append(cypher)
            st.session_state.graph.append([G,labels])
    else:
        print("Unstructured data")
        if query_mode:
            # pass
            # Generate Cypher
            cypher=gds_db.construct_cypher(user_input)
            # If not a valid Cypher statement
            if not "MATCH" in cypher:
                print('No Cypher was returned')
                st.session_state.user_input.append(user_input)
                st.session_state.generated.append(
                    cypher)
                st.session_state.cypher.append(
                    "No Cypher statement was generated")
                st.session_state.database_results.append("")
            else:
                # Query the database
                print("Will query the database")
                results = gds_db.run(cypher)
                answer = generate_response(generate_context(
                    f"Question was {user_input} and the response should include only information that is given here: {str(results)}"))
                # Graph figure
                try:
                    query = gds_db.construct_full_entity_cypher(user_input)
                    print(query)
                    G, labels = graph_from_query(query, gds_db.driver)
                except:
                    print("Error in generating graph")
                    G = nx.Graph()
                    labels = {}

                st.session_state.database_results.append(str(results))
                st.session_state.graph.append(str(results))
                st.session_state.user_input.append(user_input)
                st.session_state.generated.append(answer),
                st.session_state.cypher.append(cypher)
                st.session_state.graph.append([G,labels])
        else:
            # Insert data into the database
            if data_source == 'Simple text':
                documents_found = convert_to_graph(user_input)
                cypher = "MATCH (n)-[r]->(m) RETURN n,r,m"
                G, labels = graph_from_query(cypher, gds_db.driver)
                st.session_state.user_input.append(user_input)
                # st.session_state.generated.append("No message generated")
                st.session_state.cypher.append(cypher)
                # st.session_state.database_results.append("")
                st.session_state.graph.append([G,labels])
            else:
                # Generate Cypher
                urls = [user_input]
                documents_found = url_to_graph(urls)
                cypher = "MATCH (n)-[r]->(m) RETURN n,r,m"

                G, labels = graph_from_query(cypher, gds_db.driver)
                st.session_state.user_input.append(user_input)
                st.session_state.generated.append("No message generated")
                st.session_state.cypher.append(cypher)
                st.session_state.database_results.append("")
                st.session_state.graph.append([G,labels])
    


# Message placeholder
with placeholder.container():
    if st.session_state['generated']:
        size = len(st.session_state['generated'])
        # Display only the last three exchanges
        for i in range(max(size-3, 0), size):
            message(st.session_state['user_input'][i],
                    is_user=True, key=str(i) + '_user')
            message(st.session_state["generated"][i], key=str(i))


# Generated Cypher statements
with another_placeholder.container():
    if st.session_state['cypher']:
        st.text_area("Latest generated Cypher statement",
                     st.session_state['cypher'][-1], height=240)

with third_placeholder.container():
    if st.session_state['database_results']:
        # Try to place the graph here
        try:
            st.pyplot(nx.draw(st.session_state['graph'][-1][0], with_labels=True, labels=st.session_state['graph'][-1][1]))
        except:
            # Error gif
            st.image("https://cdn.pixabay.com/animation/2023/01/07/11/02/11-02-30-972_512.gif")
            