"""Optional Ollama/Llama3 remediation backend.

This module mirrors the advisor contract:
get_remediation_advice(anomaly_description: str) -> str
"""

import sys

import ollama
import requests


def check_ollama_status() -> bool:
    """Check that the local Ollama service is reachable before inference."""
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Error: Ollama is not running.")
        print("👉 Please start Ollama or run 'ollama serve' in your terminal.")
        return False


def get_remediation_advice(anomaly_description: str) -> str:
    """Return structured remediation advice for an anomaly description."""
    print("🧠 Analyzing anomaly data with Llama 3...")

    prompt = f"""
    You are a Senior Network Security Expert.
    Our AI system detected a network anomaly with these features:
    {anomaly_description}

    Provide a structured security report using exactly this format:

    1. 🛡️ ATTACK TYPE: (Identify the specific attack, e.g., DoS, Port Scan, Exploits)
    2. ⚠️ RISK LEVEL: (Low, Medium, High, or Critical)
    3. 🔍 TECHNICAL ANALYSIS: (Explain why these features suggest a threat)
    4. 🛠️ MITIGATION STEPS: (Provide the exact Cisco IOS Access Control List (ACL) commands to block this)

    Ensure the advice is concrete and technically accurate for a Cisco environment.
    """

    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]
    except Exception as e:
        return f"❌ Failed to get advice from Llama 3: {str(e)}"


def get_security_advice(anomaly_data: str) -> str:
    """Backward-compatible alias for older callers."""
    return get_remediation_advice(anomaly_data)


def main() -> None:
    print("\n" + "=" * 60)
    print("🛡️  NETPULSE-SHIELD: ADVANCED AI REMEDIATION")
    print("=" * 60)

    if not check_ollama_status():
        sys.exit(1)

    test_anomaly = "Sload: 1,500,000,000, sttl: 254, sbytes: 5000"
    advice = get_remediation_advice(test_anomaly)
    print("\n" + advice)
    print("\n" + "=" * 60)
    print("✅ Report generated successfully.")


if __name__ == "__main__":
    main()