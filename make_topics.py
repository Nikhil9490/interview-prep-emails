# make_topics.py
from docx import Document

topics = [
    # Block 1
    "Linear Regression | Assumptions + Cost Function",
    "Ridge & Lasso | L1 vs L2 + Feature Selection",
    "Logistic Regression | Sigmoid + Decision Boundary",
    "Generative vs Discriminative Models | Logistic vs Naive Bayes",
    "Naive Bayes | Independence Assumption + When It Wins",
    "Bias-Variance Tradeoff | Regularization Intuition",
    "REVISION",

    # Block 2
    "Cross Validation | K-Fold + Data Leakage",
    "Precision, Recall, F1 | Threshold Tuning",
    "ROC-AUC vs PR Curve | When Each Misleads",
    "Imbalanced Data | Class Weights vs SMOTE",
    "Hyperparameter Tuning | Grid vs Random",
    "Model Failure Cases | Debugging Strategy",
    "REVISION",

    # Block 3
    "Decision Trees | Gini vs Entropy",
    "Bagging vs Boosting | Core Differences",
    "Random Forest | OOB + Feature Importance Pitfalls",
    "Gradient Boosting | Additive Models Intuition",
    "XGBoost | Regularization in Boosting",
    "Support Vector Machines | Margin + Kernel Trick",
    "REVISION",

    # Block 4
    "K-Nearest Neighbors | Distance + Curse of Dimensionality",
    "K-Means | Objective + Choosing k",
    "DBSCAN | Density Clustering",
    "PCA | Variance + Dimensionality Reduction",
    "Feature Engineering | Encoding + Scaling",
    "Multicollinearity | Why It Matters",
    "REVISION",

    # Block 5
    "Missing Data | Imputation Strategies",
    "Model Selection | When Linear Beats Trees",
    "Calibration | Platt Scaling Intuition",
    "A/B Testing | Type I/II + Business Framing",
    "Correlation vs Causation | Common Traps",
    "Time Series Basics | Train/Test Splitting",
    "REVISION",

    # Block 6
    "Neural Networks | Perceptron + MLP",
    "Backpropagation | Chain Rule Intuition",
    "Activation Functions | ReLU vs Sigmoid",
    "Initialization + Vanishing Gradients",
    "Regularization in DL | Dropout + Early Stopping",
    "Optimization | SGD vs Adam + LR Scheduling",
    "REVISION",

    # Block 7
    "CNN | Convolution + Pooling",
    "Transfer Learning | Fine-tuning Strategy",
    "RNN | Sequence Modeling",
    "LSTM | Why It Exists",
    "Attention Mechanism | Q/K/V Intuition",
    "Transformers | Encoder + Self-Attention",
    "REVISION",

    # Block 8
    "Text Preprocessing | Tokenization",
    "TF-IDF | Sparse Representation",
    "Word2Vec | CBOW vs Skip-Gram",
    "Embeddings | Cosine Similarity",
    "Language Modeling | Next Token Objective",
    "Decoding | Temperature + Top-p",
    "REVISION",

    # Block 9
    "LLM Architecture | Pretraining vs Fine-tuning",
    "Instruction Tuning | Concept",
    "Fine-tuning vs Prompting | Tradeoffs",
    "Prompt Engineering | Zero vs Few-shot",
    "Hallucinations | Why They Happen",
    "Evaluation for LLMs | Faithfulness + Groundedness",
    "REVISION",

    # Block 10
    "RAG | Why + When",
    "Chunking Strategies | Size + Overlap Tradeoffs",
    "Vector Search | Cosine vs Dot vs L2",
    "FAISS | ANN Conceptual Overview",
    "Reranking | Cross-Encoder Idea",
    "RAG Failure Modes | Retrieval + Context Issues",
    "REVISION",

    # Block 11
    "Model Deployment | Batch vs API Inference",
    "Latency vs Accuracy | Tradeoffs",
    "Model Drift | Data vs Concept Drift",
    "Monitoring | Metrics to Track",
    "Experiment Tracking | Reproducibility Basics",
    "Stakeholder Communication | Explaining ML Clearly",
    "REVISION",
]

def main():
    doc = Document()
    for line in topics:
        doc.add_paragraph(line)
    doc.save("topics.docx")
    print("✅ Created valid topics.docx with", len(topics), "days.")

if __name__ == "__main__":
    main()