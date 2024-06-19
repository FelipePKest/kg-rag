import os
from openai import OpenAI
from dotenv import load_dotenv
from query_handlers.query_examples import cypher_entity


from retry import retry

load_dotenv()

api_key = os.environ.get('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)



system = f"""
You are an assistant with an ability to generate Cypher queries based off example Cypher queries.
Example Cypher queries are: \n {cypher_entity} \n
Do not response with any explanation or any other information except the Cypher query.
Do not include any quotes around the Cypher query.
You do not ever apologize and strictly generate cypher statements based of the provided Cypher examples.
Do not provide any Cypher statements that can't be inferred from Cypher examples.
Inform the user when you can't infer the cypher statement due to the lack of context of the conversation and state what is the missing context.
"""



@retry(tries=2, delay=5)
def generate_entity_query(messages):
    messages = [
        {"role": "system", "content": system}
    ] + messages
    # Make a request to OpenAI
    completions = client.chat.completions.create(model="gpt-3.5-turbo",
    messages=messages,
    temperature=0.0)
    response = completions.choices[0].message.content
    # If the model apologized, remove the first line or sentence
    if "apologi" in response:
        if "\n" in response:
            response = " ".join(response.split("\n")[1:])
        else:
            response = " ".join(response.split(".")[1:])
    return response

if __name__ == '__main__':
    print(generate_entity_query([{'role': 'user', 'content': 'What actors appeared in the Matrix?'},
                           ]))