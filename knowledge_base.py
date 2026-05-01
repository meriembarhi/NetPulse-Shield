# knowledge_base.py
"""
Base de connaissances centralisée pour les remédiations de NetPulse-Shield.
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