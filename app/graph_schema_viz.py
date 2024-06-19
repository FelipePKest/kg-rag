from neo4j import GraphDatabase
from neo4j.exceptions import CypherSyntaxError
from dotenv import load_dotenv
import openai
from query_handlers.query_examples import cypher_entity, cypher_movie_entity
import os

env = load_dotenv(".env")
print(env)
openai_key = os.environ.get('OPENAI_API_KEY')


host = os.environ.get('NEO4J_URL')
user = os.environ.get('NEO4J_USER')
password = os.environ.get('NEO4J_PASS')

aura_host = os.environ.get('NEO4J_AURA_URL')
aura_user = os.environ.get('NEO4J_AURA_USER')
aura_password = os.environ.get('NEO4J_AURA_PASS')

print(host, user, password)
# print(aura_host, aura_user, aura_password)

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
    def __init__(self, url, user, password, openai_api_key, AURA=False):
        self.driver = GraphDatabase.driver(url, auth=(user, password))
        self.IS_AURA = AURA
        openai.api_key = openai_api_key
        # construct schema
        self.schema = self.generate_schema()
        self.client = openai.OpenAI(api_key=openai_api_key)

    def generate_schema(self):
        node_props = self.query_database(node_properties_query)
        rel_props = self.query_database(rel_properties_query)
        rels = self.query_database(rel_query)
        return schema_text(node_props, rel_props, rels)

    def refresh_schema(self):
        self.schema = self.generate_schema()

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
        else:
            return f"""
            Task: Generate Cypher queries to query a Neo4j graph database based on the provided schema definition.
            Instructions:
            Use only the provided relationship types and properties.
            Do not use any other relationship types or properties that are not provided.
            If you cannot generate a Cypher statement based on the provided schema, explain the reason to the user.
            Return the full entities and named relations of the query, such as theses examples {cypher_movie_entity}
            
            Schema:
            {self.schema}

            Note: Do not include any explanations or apologies in your responses.
            """

    def query_database(self, neo4j_query, params={}):
        with self.driver.session() as session:
            result = session.run(neo4j_query, params)
            output = [r.values() for r in result]
            output.insert(0, result.keys())
            return output

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

        print("Schema ", self.schema)
        completions = self.client.chat.completions.create(model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.0)
        
        return completions.choices[0].message.content
    
    def run(self, question, history=None, retry=True):
        # Construct Cypher statement
        cypher = self.construct_cypher(question, history)
        print("Cypher", cypher)
        try:
            return self.query_database(cypher)
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
        
gds_db = Neo4jGPTQuery(
    url=aura_host,
    user=aura_user,
    password=aura_password,
    openai_api_key=openai_key,
    AURA=True
)

movies_gds_db = Neo4jGPTQuery(
    url=host,
    user=user,
    password=password,
    openai_api_key=openai_key,
)



if __name__ == '__main__':
    # print(gds_db.run("""
    #     Which players Botafogo has?
    # """))
    # gds_db.driver.close()
    # print(movies_gds_db.run("""
    #     What movies has Tom Hanks appeared in?
    # """))
    # movies_gds_db.driver.close()
    driver = GraphDatabase.driver(host, auth=(user, password))
