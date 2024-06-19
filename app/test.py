from response_handlers.response2networkx import graph_from_query, generate_entity_query_context

import os
import networkx as nx
import matplotlib.pyplot as plt
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship
from dotenv import load_dotenv
from query_handlers.entity_query import generate_entity_query
from graph_schema_viz import gds_db, movies_gds_db


load_dotenv()

host = os.environ.get('NEO4J_URL')
user = os.environ.get('NEO4J_USER')
password = os.environ.get('NEO4J_PASS')




if __name__ == '__main__':
    print(gds_db.run("""
        Who's Fluminense playing against"?
    """))
    gds_db.driver.close()
    print(movies_gds_db.run("""
        What movies has Tom Hanks appeared in?
    """))
    movies_gds_db.driver.close()