"""
Test set and evaluation script for the FinOps RAG system.
Evaluates:
1. Retrieval quality (Recall@k)
2. Answer quality (1-5 scale)
"""
import json
import os
from typing import List, Dict
import numpy as np
from app.rag_qa import answer as rag_answer
from app.rag import retrieve
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
## 
TEST_SET = [
    {
        "id": 1,
        "question": "What should I do about unassigned resources?",
        "expected_answer": "Resources should be assigned owners and environments for proper cost attribution. Check the FinOps documentation for tagging policies.",
        "relevant_chunks": ["unassigned", "owner", "tag", "coverage"],
        "context_required": ["tagging policy", "resource ownership"]
    },
    {
        "id": 2,
        "question": "How can I reduce costs in the development environment?",
        "expected_answer": "Review dev resources for optimization opportunities like shutting down outside business hours and right-sizing instances.",
        "relevant_chunks": ["development", "cost optimization", "shutdown"],
        "context_required": ["environment costs", "optimization recommendations"]
    },
    {
        "id": 3,
        "question": "Which team has the highest cloud spending?",
        "expected_answer": "Based on current data, identify the team with highest costs and spending patterns.",
        "relevant_chunks": ["team", "cost by owner", "monthly cost"],
        "context_required": ["cost by owner data", "team spending"]
    },
    {
        "id": 4,
        "question": "What is our current owner coverage percentage?",
        "expected_answer": "Owner coverage shows percentage of resources with assigned owners vs unassigned.",
        "relevant_chunks": ["owner coverage", "unassigned resources"],
        "context_required": ["coverage metrics", "resource assignments"]
    },
    {
        "id": 5,
        "question": "How has our monthly spending trend changed?",
        "expected_answer": "Analysis of month-over-month cost changes and identification of significant variations.",
        "relevant_chunks": ["monthly trend", "cost changes"],
        "context_required": ["monthly costs", "trend analysis"]
    },
    {
        "id": 6,
        "question": "What are our main cost drivers?",
        "expected_answer": "Identification of top services or resources contributing to costs.",
        "relevant_chunks": ["cost drivers", "expensive resources"],
        "context_required": ["cost breakdown", "resource costs"]
    },
    {
        "id": 7,
        "question": "Are there any idle resources we should address?",
        "expected_answer": "Identify unused or underutilized resources that could be optimized or terminated.",
        "relevant_chunks": ["idle resources", "utilization"],
        "context_required": ["resource usage", "optimization opportunities"]
    },
    {
        "id": 8,
        "question": "What's our cost split between environments?",
        "expected_answer": "Breakdown of costs between production, development, and staging environments.",
        "relevant_chunks": ["environment costs", "prod", "dev", "staging"],
        "context_required": ["environment distribution", "cost allocation"]
    },
    {
        "id": 9,
        "question": "Have there been any unusual cost spikes recently?",
        "expected_answer": "Detection of anomalous spending patterns or unexpected cost increases.",
        "relevant_chunks": ["cost spike", "anomaly"],
        "context_required": ["cost patterns", "anomaly detection"]
    },
    {
        "id": 10,
        "question": "What are the recommended cost optimization actions?",
        "expected_answer": "List of specific actions to optimize costs based on current analysis.",
        "relevant_chunks": ["optimization", "recommendations"],
        "context_required": ["optimization recommendations", "action items"]
    }
]

def evaluate_retrieval(k_values: List[int] = [1, 3, 5]) -> Dict:
    """
    Evaluate retrieval quality using Recall@k
    """
    results = {f"recall@{k}": [] for k in k_values}
    
    for test_case in TEST_SET:
        # Get retrieved documents
        retrieved_chunks = retrieve(test_case["question"], top_k=max(k_values))
        retrieved_text = [chunk["text"].lower() for chunk in retrieved_chunks]
        
        # Calculate recall@k for each k
        for k in k_values:
            relevant_found = 0
            for keyword in test_case["relevant_chunks"]:
                # Check if any of the top-k retrieved chunks contain this keyword
                for chunk in retrieved_text[:k]:
                    if keyword.lower() in chunk:
                        relevant_found += 1
                        break
            
            recall = relevant_found / len(test_case["relevant_chunks"])
            results[f"recall@{k}"].append(recall)
    
    # Calculate average recall for each k
    final_results = {}
    for k in k_values:
        final_results[f"recall@{k}"] = np.mean(results[f"recall@{k}"])
    
    return final_results

def evaluate_answer_quality(save_results: bool = True) -> Dict:
   
    results = []
    
    for test_case in TEST_SET:
        # Get answer from RAG system
        response = rag_answer(test_case["question"])
        
        result = {
            "id": test_case["id"],
            "question": test_case["question"],
            "expected_answer": test_case["expected_answer"],
            "system_answer": response.get("answer", "No answer generated"),
            "context_required": test_case["context_required"],
            "quality_score": None,  # To be filled manually
            "notes": ""  # For manual evaluation notes
        }
        results.append(result)
    
    if save_results:
        with open("tests/rag_eval_results.json", "w") as f:
            json.dump(results, f, indent=2)
    
    return results

def print_evaluation_summary(retrieval_results: Dict, answer_results: List):
    """Print a summary of evaluation results"""
    print("\nRetrieval Evaluation:")
    print("-" * 50)
    for metric, value in retrieval_results.items():
        print(f"{metric}: {value:.3f}")
    
    print("\nAnswer Quality Evaluation:")
    print("-" * 50)
    print("Results saved to tests/rag_eval_results.json")
    print("Please manually rate answer quality using the following rubric:")
    print("1 - Completely irrelevant or incorrect")
    print("2 - Partially relevant but major issues")
    print("3 - Relevant but some inaccuracies")
    print("4 - Accurate but could be more complete")
    print("5 - Perfect answer meeting all requirements")

if __name__ == "__main__":
    os.makedirs("tests", exist_ok=True)
    
    # Run evaluations
    print("Evaluating retrieval quality...")
    retrieval_results = evaluate_retrieval()
    
    print("\nGenerating answers for quality evaluation...")
    answer_results = evaluate_answer_quality()
    

    print_evaluation_summary(retrieval_results, answer_results)