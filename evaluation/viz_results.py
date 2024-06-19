import matplotlib.pyplot as plt
import numpy as np

scores = np.load("evaluation/scores.npy")
plt.hist(scores, bins=20)
plt.xlabel('Similarity')
plt.ylabel('Frequency')
plt.show()