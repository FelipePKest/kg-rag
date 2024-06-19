import os
import networkx as nx
import matplotlib.pyplot as plt
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship
from dotenv import load_dotenv
# from entity_query import generate_entity_query

load_dotenv()

def graph_from_query(query, driver, test_db=False):
    # # Create a NetworkX graph
    """Constructs a networkx graph from the results of a neo4j cypher query.
    Example of use:
    >>> result = session.run(query)
    >>> G = graph_from_cypher(result.data())

    Nodes have fields 'labels' (frozenset) and 'properties' (dicts). Node IDs correspond to the neo4j graph.
    Edges have fields 'type_' (string) denoting the type of relation, and 'properties' (dict)."""

    G = nx.MultiDiGraph()
    labels = {}
    def add_node(node):
        # Adds node id it hasn't already been added
        u = node.id
        if G.has_node(u):
            return
        else:
            print("Adding node", u)
            G.add_node(u, labels=node._labels, properties=dict(node))

    def add_edge(relation):
        # Adds edge if it hasn't already been added.
        # Make sure the nodes at both ends are created
        for node in (relation.start_node, relation.end_node):
            add_node(node)
        # Check if edge already exists
        u = relation.start_node.id
        v = relation.end_node.id
        eid = relation.id
        if G.has_edge(u, v, key=eid):
            return
        # If not, create it
        else:
            G.add_edge(u, v, key=eid, type_=relation.type, properties=dict(relation))

    # with driver.session() as session:
    print("Entity query",query)
    result = driver.session().run(query)
    # print("Entity query result",result.values())
    for d in result:
        for entry in d.values():
            # Parse node
            if isinstance(entry, Node):
                add_node(entry)
                if entry.id not in labels.keys():
                    if test_db:
                        print("Test_DB")
                        if "Movie" in entry.labels:
                            labels[entry.id] = entry._properties.get("title")
                        elif "Person" in entry.labels:
                            labels[entry.id] = entry._properties.get("name")
                        print(labels[entry.id])
                        
                    else:
                        labels[entry.id] = entry._properties.get("id")
                    print(labels[entry.id])
            # Parse link
            elif isinstance(entry, Relationship):
                add_edge(entry)
            else:
                raise TypeError("Unrecognized object")
    return G, labels

def generate_entity_query_context(prompt):
    context = []
    context.append({'role': 'user', 'content': str(prompt)})
    return context

