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

import os
import sys
from advisor import NetworkSecurityAdvisor

def main():
    # --- STEP 1: SAFETY CHECK ---
    # Verify if the detector has been run and generated the alert file
    ALERT_FILE = "alerts.csv"
    
    if not os.path.exists(ALERT_FILE):
        print("\n" + "="*55)
        print("🛡️  NETPULSE-SHIELD: SYSTEM ERROR")
        print("="*55)
        print(f"❌ Could not find: {ALERT_FILE}")
        print("👉 Action Required: Run 'python detector.py' first to identify anomalies.")
        print("="*55 + "\n")
        sys.exit(1)

    # --- STEP 2: INITIALIZATION ---
    print("🛡️ NetPulse-Shield — RAG Advisor (Modular)")
    print("✅ Alerts detected. Initializing RAG Remediation Pipeline...")
    
    # Initializes the advisor (loads knowledge base and builds vector store)
    advisor = NetworkSecurityAdvisor()

    # --- STEP 3: PROCESSING ---
    # Example Query (You can later update this to loop through your alerts.csv)
    query = "Lateral movement detected via internal port scanning on port 445."
    
    print(f"\n[ANALYSIS] Query: {query}")
    print("-" * 55)
    
    # Get and print the remediation advice
    report = advisor.get_remediation_advice(query)
    print(report)

if __name__ == "__main__":
    main()
