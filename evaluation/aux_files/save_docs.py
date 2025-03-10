
from  langchain.schema import Document
import pandas as pd
import json
from typing import Iterable

def save_docs_to_jsonl(array:Iterable[Document], file_path:str)->None:
    with open(file_path, 'w') as jsonl_file:
        for doc in array:
            jsonl_file.write(doc.json() + '\n')

def load_docs_from_jsonl(file_path)->Iterable[Document]:
    array = []
    with open(file_path, 'r') as jsonl_file:
        for line in jsonl_file:
            data = json.loads(line)
            obj = Document(**data)
            array.append(obj)
    return array
    
# save_docs_to_jsonl(docs,'data.jsonl')
df = pd.read_csv('testset.csv').to_json('testset.jsonl',orient='records',lines=True)

# docs2=load_docs_from_jsonl('data.jsonl')
# print(len(docs2))