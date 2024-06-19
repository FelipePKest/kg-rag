from neo4j import GraphDatabase
from neo4j.exceptions import CypherSyntaxError
from dotenv import load_dotenv
import openai
# from query_handlers.query_examples import cypher_entity, cypher_movie_entity
import os

load_dotenv()

openai_key = os.environ.get('OPENAI_API_KEY')
host = os.environ.get('NEO4J_URL')
user = os.environ.get('NEO4J_USER')
password = os.environ.get('NEO4J_PASS')

aura_host = os.environ.get('NEO4J_AURA_URL')
aura_user = os.environ.get('NEO4J_AURA_USER')
aura_password = os.environ.get('NEO4J_AURA_PASS')


cypher_entity = """
# What movies did Keanu Reeves act in?
MATCH (p: Person {id: "Keanu Reeves"}) -[r: ACTED_IN]->(movie)
RETURN p, r, movie;
# What movies did Leonardo DiCaprio direct?
MATCH (p: Person {id: "Leonardo DiCaprio"}) -[r: DIRECTED]->(movie)
RETURN p, r, movie;
# What actors played in The Matrix?
MATCH (m: Movie {id: "The Matrix"}) <-[r: ACTED_IN]-(a)
RETURN m, r, a;
# Which movies are in the Action genre?
MATCH (m: Movie) -[r: IN_GENRE]->(g: Genre {id: "Action"})
RETURN m, r, g;
"""

def schema_text(node_props, rel_props, rels):
    return f"""
  This is the schema representation of the Neo4j database.
  Node properties are the following:
  {node_props}
  Relationship properties are the following:
  {rel_props}
  Relationship point from source to target nodes
  {rels}
  Make sure to respect relationship types and directions
  """


node_properties_query = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "node"
WITH label AS nodeLabels, collect(property) AS properties
RETURN {labels: nodeLabels, properties: properties} AS output

"""

rel_properties_query = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "relationship"
WITH label AS nodeLabels, collect(property) AS properties
RETURN {type: nodeLabels, properties: properties} AS output
"""

rel_query = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE type = "RELATIONSHIP" AND elementType = "node"
RETURN {source: label, relationship: property, target: other} AS output
"""


def schema_text(node_props, rel_props, rels):
    return f"""
  This is the schema representation of the Neo4j database.
  Node properties are the following:
  {node_props}
  Relationship properties are the following:
  {rel_props}
  Relationship point from source to target nodes
  {rels}
  Make sure to respect relationship types and directions
  """


class Neo4jGPTQuery:


    _instance = None

    def __init__(self, host=host, user=user, password=password, openai_api_key=openai_key, AURA=False):
        self.driver = GraphDatabase.driver(host, auth=(user, password))
        self.IS_AURA = AURA
        
        openai.api_key = openai_api_key
        # construct schema
        with self.driver.session() as session:
            self.schema = self.generate_schema(session)
        self.driver.close()
        self.client = openai.OpenAI(api_key=openai_api_key)
    
    @staticmethod
    def get_instance():
        if not Neo4jGPTQuery._instance:
            Neo4jGPTQuery._instance = Neo4jGPTQuery(host=aura_host,
                                                    user=aura_user,
                                                    password=aura_password,
                                                    openai_api_key=openai_key)
        return Neo4jGPTQuery._instance

    def generate_schema(self,session):
        node_props = self.query_database(node_properties_query, session)
        rel_props = self.query_database(rel_properties_query, session)
        rels = self.query_database(rel_query, session)
        return schema_text(node_props, rel_props, rels)

    def refresh_schema(self):
        self.schema = self.generate_schema()

    def start_session(self):
        return self.driver.session()
    
    def query_database(self, neo4j_query, session, params={}):
        # with self.driver.session() as session:
        result = session.run(neo4j_query, params)
        output = [r.values() for r in result]
        # output.insert(0, result.keys())
        # print("Output2 ==========", output)
        return output

    def get_system_message(self):
        return f"""
        Task: Generate Cypher queries to query a Neo4j graph database based on the provided schema definition.
        Instructions:
        Use only the provided relationship types and properties.
        Do not use any other relationship types or properties that are not provided.
        If you cannot generate a Cypher statement based on the provided schema, explain the reason to the user.
        Schema:
        {self.schema}

        Note: Do not include any explanations or apologies in your responses.
        """
    def get_system_entity_message(self):
        if self.IS_AURA:
            return f"""
            Task: Generate Cypher queries to query a Neo4j graph database based on the provided schema definition.
            Instructions:
            Use only the provided relationship types and properties.
            Do not use any other relationship types or properties that are not provided.
            If you cannot generate a Cypher statement based on the provided schema, explain the reason to the user.
            Return the full entities and named relations of the query, such as theses examples {cypher_entity}
            
            Schema:
            {self.schema}

            Note: Do not include any explanations or apologies in your responses.
            """

    def construct_cypher(self, question, history=None):
        messages = [
            {"role": "system", "content": self.get_system_message()},
            {"role": "user", "content": question},
        ]
        # Used for Cypher healing flows
        if history:
            messages.extend(history)

        completions = self.client.chat.completions.create(model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.0)
        
        return completions.choices[0].message.content

    def construct_full_entity_cypher(self, question, history=None):
        messages = [
            {"role": "system", "content": self.get_system_entity_message()},
            {"role": "user", "content": question},
        ]
        print("DATABASE USED == ", self.IS_AURA)
        # Used for Cypher healing flows
        if history:
            print("History", history)
            messages.extend(history)

        completions = self.client.chat.completions.create(model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.0)
        
        return completions.choices[0].message.content
    
    def text_from_response(self, response):
        completions = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "assistant",
                 "content": "Rewrite the following query response to a human readable text containing only the entities' id: \n" + response + ". If you can't provide an acceptable text, leave the text as an empty string."
                }
            ],
            temperature=0.0)
        return completions.choices[0].message.content
    
    def run(self, question, history=None, retry=True, readable=True):
        # Construct Cypher statement
        cypher = self.construct_cypher(question, history)
        print(cypher)
        try:
            with self.start_session() as session:
                response = self.query_database(cypher, session=session)
                if readable:
                    return self.text_from_response(str(response))
                return response
        # Self-healing flow
        except CypherSyntaxError as e:
            # If out of retries
            if not retry:
              return "Invalid Cypher syntax"
        # Self-healing Cypher flow by
        # providing specific error to GPT-4
            print("Retrying")
            return self.run(
                question,
                [
                    {"role": "assistant", "content": cypher},
                    {
                        "role": "user",
                        "content": f"""This query returns an error: {str(e)} 
                        Give me a improved query that works without any explanations or apologies""",
                    },
                ],
                retry=False
            )
    
    def run_question(self, question, history=None, retry=True, readable=True):
        # Construct Cypher statement
        history = [{"role": "assistant", "content": "On the response of the query, you must return only the node's, or nodes', id propery "}]
        cypher = self.construct_cypher(question, history)
        print(cypher)
        try:
            with self.start_session() as session:
                response = self.query_database(cypher, session=session)
                if readable:
                    return self.text_from_response(str(response))
                return response
        # Self-healing flow
        except CypherSyntaxError as e:
            # If out of retries
            if not retry:
              return "Invalid Cypher syntax"
        # Self-healing Cypher flow by
        # providing specific error to GPT-4
            print("Retrying")
            return self.run(
                question,
                [
                    {"role": "assistant", "content": cypher},
                    {
                        "role": "user",
                        "content": f"""This query returns an error: {str(e)} 
                        Give me a improved query that works without any explanations or apologies""",
                    },
                ],
                retry=False
            )
graph_db = Neo4jGPTQuery.get_instance()
