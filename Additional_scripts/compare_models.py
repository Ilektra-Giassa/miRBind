#!/usr/bin/env python

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve
from sklearn import metrics
from tensorflow import keras as K

def load_cofold(name):
    f = open(name, 'r')
    scores = []
    while True:
        _ = f.readline()
        _ = f.readline()
        line3 = f.readline()
        if not line3:
            break
        ll = line3.split()
        score = -float(ll[-1].replace("(", "")[:-2])
        scores.append(score)
    minimum = min(scores)
    maximum = max(scores)
    norm = [(val - minimum) / (maximum - minimum) for val in scores]
    return norm, scores


def load_rna22(name, pos_count, neg_count):
    """_summary_

    Args:
        name (str): path to data file
        pos_count (int): count of positive examples in original test file
        neg_count (int): count of negative examples in original test file

    Returns:
        tuple(np.array, np.array): array of labels and array of normalized score
    """

    rna22 = pd.read_csv(name, header=None, usecols=[10,11], names=['score', 'label'], sep='\t')
    # they use p-value so we need to invert in to use it as score
    rna22['score'] = rna22['score'].apply(lambda x: 1 - x)

    # normalizing to the whole 0-1 interval
    minimum = min(rna22['score'])
    maximum = max(rna22['score'])
    rna22['norm'] = rna22['score'].apply(lambda x: (x - minimum) / (maximum - minimum))

    # we don't have results for all sequences - adding score 0 for missing ones
    pos = pos_count - rna22['label'].value_counts()[1]
    neg = neg_count - rna22['label'].value_counts()[0]
    added_score = []
    for i in range(pos):
        added_score.append([0, 1, 0])
    for i in range(neg):
        added_score.append([0, 0, 0])

    rna22 = pd.concat([rna22, pd.DataFrame(added_score, columns=['score', 'label', 'norm'])], ignore_index=True)

    return np.array(rna22['label']), np.array(rna22['norm'])


def one_hot_encoding(df, tensor_dim=(50, 20, 1)):
    # alphabet for watson-crick interactions.
    alphabet = {"AT": 1., "TA": 1., "GC": 1., "CG": 1.}
    # labels to one hot encoding
    label = df["label"].to_numpy()
    # create empty main 2d matrix array
    N = df.shape[0]  # number of samples in df
    shape_matrix_2d = (N, *tensor_dim)  # 2d matrix shape
    # initialize dot matrix with zeros
    ohe_matrix_2d = np.zeros(shape_matrix_2d, dtype="float32")

    # compile matrix with watson-crick interactions.
    for index, row in df.iterrows():
        for bind_index, bind_nt in enumerate(row.gene.upper()):
            for mirna_index, mirna_nt in enumerate(row.miRNA.upper()):
                base_pairs = bind_nt + mirna_nt
                ohe_matrix_2d[index, bind_index, mirna_index, 0] = alphabet.get(base_pairs, 0)

    return ohe_matrix_2d, label


def seed_match(miRNA, gene):
    alphabet = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
    seed = miRNA[1:7]
    seed = ''.join([alphabet[s] for s in seed][::-1])
    return seed in gene


def seed_pr(data):
    TP = 0
    FP = 0
    TN = 0
    FN = 0
    for index, row in data.iterrows():
        if seed_match(row['miRNA'].upper(), row['gene'].upper()):
            if row['label'] == 1:
                TP += 1
            else:
                FP += 1
        elif row['label'] == 1:
            FN += 1
        else:
            TN += 1
    return TP / (TP + FP), TP / (TP + FN)


dataset_ratio = '1'
df = pd.read_csv("../Datasets/test_set_1_" + dataset_ratio + "_CLASH2013_paper.tsv", sep='\t')
ohe_data = one_hot_encoding(df)
seq_ohe, labels = ohe_data
print("Number of samples: ", df.shape[0])

model_1 = K.models.load_model("../Models/model_1_1.h5")
model_1_predictions = model_1.predict(seq_ohe)
model_10 = K.models.load_model("../Models/model_1_10.h5")
model_10_predictions = model_10.predict(seq_ohe)
model_100 = K.models.load_model("../Models/model_1_100.h5")
model_100_predictions = model_100.predict(seq_ohe)

plt.figure(figsize=(4, 4), dpi=250)

precision, recall, _ = precision_recall_curve(labels, model_1_predictions)
print("Model 1:1 auc", metrics.auc(recall, precision))
plt.plot(recall, precision, label='miRBind1', marker=',', color='#00429d')

precision, recall, _ = precision_recall_curve(labels, model_10_predictions)
print("Model 1:10 auc", metrics.auc(recall, precision))
plt.plot(recall, precision, label='miRBind10', marker=',', color='#73a2c6')

precision, recall, _ = precision_recall_curve(labels, model_100_predictions)
print("Model 1:100 auc", metrics.auc(recall, precision))
plt.plot(recall, precision, label='miRBind100', marker=',', color='#a5d5d8')


cofold, cofold_orig = load_cofold("../Datasets/test_set_1_" + dataset_ratio + "_CLASH2013_paper_cofold.fasta")

precision, recall, _ = precision_recall_curve(labels, np.array(cofold))
print("Cofold auc ", metrics.auc(recall, precision))
plt.plot(recall, precision, label='Cofold', marker=',', color='#f3b77d')


rna22_labels, rna22_probs = load_rna22("../Datasets/test_set_1_" + dataset_ratio + "_CLASH2013_paper_rna22.txt", 2000, dataset_ratio*2000)
precision, recall, _ = precision_recall_curve(rna22_labels, rna22_probs)
print("RNA22 auc ", metrics.auc(recall, precision))
plt.plot(recall, precision, label='RNA22', marker=',', color='#388294')


prec, sens = seed_pr(df)
plt.plot(sens, prec, label='Seed', marker='.', color='#de425b')
print("Seed sens, prec: ", sens, prec)

plt.legend(loc='best')
plt.axis([0, 1, 0, 1])
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('PR curve on 1:' + dataset_ratio + ' test set')
plt.savefig('PR_test_set_1_' + dataset_ratio + '.png')