"""
This module serves as the Centralized Intelligence Store for NetPulse-Shield. It acts as a 
specialized repository that houses expert-vetted cybersecurity data, specifically curated for 
network engineering contexts.

Key Technical Operations:

Expert Taxonomy: It organizes cyber threats into distinct categories (e.g., DDoS, Lateral 
Movement, C2) to ensure the AI has a structured map of the threat landscape.  

Indicator Correlation: Each entry includes specific Indicators of Compromise (IoCs), allowing 
the system to match technical "symptoms" like packet spikes or unusual ports to the correct 
attack type.

Actionable Remediation: It provides high-level mitigation strategies that are ready for 
implementation by a network administrator.



Detailed Technical Breakdown:
Here is the professional description explained piece by piece:

1. "Centralized Intelligence Store"
Instead of having security advice scattered everywhere, you have one single "Source of Truth".
This makes your code clean because whenever the AI needs to know how to fix a problem, it knows
exactly which file to open. 

2. "Expert Taxonomy"
A "Taxonomy" is just a fancy word for Classification.
You don't just have a giant pile of text. You have organized categories: DDoS, Lateral Movement,
and C2.  This structure helps the AI "understand" the specific type of threat it is dealing 
with so it doesn't give "DDoS" advice for a "Password Attack".  

3. "Indicator Correlation"
The file contains Indicators of Compromise (IoCs).  These are the "fingerprints" of an attack 
(for example: "high frequency of failed logins").  The code uses these indicators to correlate 
(connect) the raw numbers from your network to a specific name of an attack. 

4. "Actionable Remediation"
The information in this file isn't just theory; it is actionable. It provides specific commands 
or steps (like "Block IP at firewall" or "Enable MFA") that a human can actually do to stop the
hacker.
"""

_BUILTIN_KNOWLEDGE = """
# DDoS Attack Remediation
Indicators: Sudden spike in packets_per_second, high bytes_sent.
Remediation: 1. Enable rate-limiting. 2. Activate scrubbing services.

# Lateral Movement Remediation
Indicators: Internal scanning of SMB/port 445, unusual SSH connections between internal workstations.
Remediation: 1. Isolate compromised hosts. 2. Implement micro-segmentation. 3. Audit internal access logs.

# Credential Stuffing Remediation
Indicators: High frequency of failed login attempts on SSH (22) or Web (443) from the same source.
Remediation: 1. Ban source IP via Fail2Ban. 2. Enforce MFA. 3. Reset affected passwords.

# C2 (Command & Control) Remediation
Indicators: Periodic beaconing to external IPs, unauthorized DNS tunneling, unusual outbound traffic.
Remediation: 1. Block C2 IP/domain at firewall. 2. Inspect outbound DNS queries. 3. Sinkhole malicious domains.
"""

def load_knowledge_base(path=None):
    from pathlib import Path
    if path and Path(path).is_file():
        return Path(path).read_text(encoding="utf-8")
    return _BUILTIN_KNOWLEDGE