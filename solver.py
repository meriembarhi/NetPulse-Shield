"""
solver.py - RAG remediation helper for NetPulse-Shield

This script validates that alerts.csv exists, then loads the advisor and
prints remediation guidance for a sample anomaly description.
"""

import os
import sys
from advisor import NetworkSecurityAdvisor

def main():
    # --- STEP 1: SAFETY CHECK ---
    # Verify that the detector has generated the alert file
    ALERT_FILE = "alerts.csv"
    
    if not os.path.exists(ALERT_FILE):
        print("\n" + "="*55)
        print("🛡️  NETPULSE-SHIELD: Missing Alerts File")
        print("="*55)
        print(f"❌ Could not find: {ALERT_FILE}")
        print("👉 Action required: run 'python pipeline.py' or 'python detector.py' first.")
        print("="*55 + "\n")
        sys.exit(1)

    # --- STEP 2: INITIALIZATION ---
    print("🛡️ NetPulse-Shield — Remediation Advisor")
    print("✅ Alerts detected. Initializing the advisor...")
    
    # Initialize the advisor (loads the knowledge base and builds the vector store)
    advisor = NetworkSecurityAdvisor()

    # --- STEP 3: PROCESSING ---
    # Example query (this can be replaced with per-alert processing later)
    query = "Lateral movement detected via internal port scanning on port 445."
    
    print(f"\n[ANALYSIS] Query: {query}")
    print("-" * 55)
    
    # Get and print the remediation advice
    report = advisor.get_remediation_advice(query)
    print(report)

if __name__ == "__main__":
    main()
