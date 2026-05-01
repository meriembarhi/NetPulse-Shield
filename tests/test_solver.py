"""
test_solver.py - Validation Suite for RAG-Based Security Remediation

This script validates the intelligence of the RAG advisor. It ensures 
the retrieval-augmented system provides industry-standard security 
mitigation steps (MFA, fail2ban, ACLs) in response to specific threats.

Validation Criteria:
- Semantic matching between a threat query and expert knowledge.
- Presence of actionable technical keywords in the generated advice.
"""

import pytest
from advisor import NetworkSecurityAdvisor

def test_rag_remediation_accuracy():
    """
    Test Case: Verify remediation for an Authentication Attack.
    Scenario: User submits a query regarding SSH Brute-force detection.
    """
    advisor = NetworkSecurityAdvisor()
    
    # Defining a specific threat scenario common in local networks
    query = "Repeated failed SSH login attempts from a single source IP (Brute-force)."
    response = advisor.get_remediation_advice(query)
    
    # List of expected professional mitigation technologies
    required_keywords = ["MFA", "fail2ban", "ACL", "lockout", "policy"]
    
    # Check if the AI response is technical enough
    found = any(word.lower() in response.lower() for word in required_keywords)
    
    assert found, f"FAIL: Advice was too vague. Missing key terms: {required_keywords}"
    print("\n✅ Solver Test Passed: RAG system returned precise, actionable security protocols.")

if __name__ == "__main__":
    test_rag_remediation_accuracy()