"""
solver.py - Orchestrator for the NetPulse-Shield RAG Remediation System

This script acts as the main entry point for the AI-powered advisor. It 
coordinates the modular components (knowledge base, embeddings, and advisor) 
to process detected anomalies and generate actionable security reports.

Workflow
--------
1.  Initializes the NetPulseAdvisor (which loads the knowledge base and 
    builds the vector store via advisor.py and embeddings.py).
2.  Takes anomaly descriptions (from alerts.csv or manual input).
3.  Triggers the retrieval process to find expert remediation steps.
4.  Outputs a structured security report for the network administrator.
"""

# solver.py
from advisor import NetworkSecurityAdvisor

if __name__ == "__main__":
    print("🛡️ NetPulse-Shield — RAG Advisor (Modular)")
    advisor = NetworkSecurityAdvisor()
    query = "Lateral movement detected via internal port scanning on port 445."
    print(f"\nQuery: {query}\n" + "-"*50)
    print(advisor.get_remediation_advice(query))
