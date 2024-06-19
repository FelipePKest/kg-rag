from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from ragas.metrics import answer_similarity
# from ragas import evaluate
# from datasets import Dataset

from dotenv import load_dotenv
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from aux_files.graph_db import graph_db


load_dotenv()

embeddings = OpenAIEmbeddings()

langchain_data = {}

# Get questions from the testset
testset = pd.read_csv("evaluation/in_graph_testset.csv")
questions = testset["Pergunta"].tolist()
ground_truth = testset["Resposta"].tolist()

result_df = pd.DataFrame(columns=["Pergunta", "Resposta", "Resposta do Grafo", "Score", "Classificação"])

scores = []
classification = []
for i in range(len(questions)):
    answer = str(graph_db.run_question(questions[i], readable=False))
    answer = answer.replace("[", "")
    answer = answer.replace("]", "")
    answer = answer.replace("'", "")
    print("Pergunta ==========", questions[i])
    print("Verdade  ==========", ground_truth[i])
    print("Resposta ==========", answer)
    
    if (answer == "Invalid Cypher syntax" or answer == "" or answer == "Empty"):
        score = 0
        scores.append(score)
        classification.append("Wrong Cypher")
        df = pd.DataFrame({"Pergunta": [questions[i]], "Resposta": [ground_truth[i]], "Resposta do Grafo": [answer], "Score": [score], "Classificação": [classification[-1]]})
        result_df = pd.concat([result_df,df], ignore_index=True, axis=0)
        continue



    embedding_1 = np.array(embeddings.embed_query(ground_truth[i]))
    # embedding_1 = np.array(embeddings.embed_query(ground_truth))
    embedding_2 = np.array(embeddings.embed_query(answer))
    # Normalization factors of the above embeddings
    norms_1 = np.linalg.norm(embedding_1, keepdims=True)
    norms_2 = np.linalg.norm(embedding_2, keepdims=True)
    embedding_1_normalized = embedding_1 / norms_1
    embedding_2_normalized = embedding_2 / norms_2
    similarity = embedding_1_normalized @ embedding_2_normalized.T
    score = similarity.flatten()[0]
    print("Score ==========", score)
    if score > 0.85:
        classification.append("Correct")
    else:
        classification.append("Wrong")
    scores.append(score)
 
    df = pd.DataFrame({"Pergunta": [questions[i]], "Resposta": [ground_truth[i]], "Resposta do Grafo": [answer], "Score": [score], "Classificação": [classification[-1]]})
    result_df = pd.concat([result_df,df], ignore_index=True, axis=0)
    

freq = [0,0,0]
x = ["Correct", "Wrong", "Wrong Cypher"]

for i in classification: 
    if i == "Correct":
        freq[0] += 1
    elif i == "Wrong":
        freq[1] += 1
    else:
        freq[2] += 1

now = datetime.now()
timestamp = now.strftime("%d_%m_%H_%M")
save_name = "evaluation/results/evaluation_results_"
save_path = str.join("", [save_name,timestamp,".csv"])
result_df.to_csv(save_path, index=False)

plt.subplot(1, 2, 1)
plt.hist(scores)
plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
# make x axis start from 0
plt.xlim(0, 1.01)
plt.title("Scores")
plt.ylabel("Scores")

plt.subplot(1, 2, 2)
plt.bar(x, freq, color=['green', 'orange', 'yellow'])
plt.title("Classification")
plt.ylabel("Frequency")
plt.show()



graph_db.driver.close()