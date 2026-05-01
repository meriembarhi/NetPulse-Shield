"""
remediator.py - Advanced AI Synthesis & Cisco Command Generator

This module acts as a high-level alternative to the RAG advisor. 
It interfaces directly with a local Llama 3 instance via Ollama 
to synthesize detected network threats into concrete remediation 
scripts. It is specifically tuned to output Cisco IOS configurations, 
allowing for rapid response and infrastructure hardening.
"""

import ollama
import sys
import requests

def check_ollama_status():
    """Vérifie si le serveur Ollama est actif avant de lancer l'analyse."""
    try:
        # Le port par défaut d'Ollama est 11434
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Error: Ollama is not running.")
        print("👉 Please start Ollama or run 'ollama serve' in your terminal.")
        return False

def get_security_advice(anomaly_data):
    """Interroge Llama 3 pour obtenir un diagnostic et une commande Cisco ACL."""
    print(f"🧠 Analyzing anomaly data with Llama 3...")
    
    # Le prompt définit le rôle d'expert et le format de sortie attendu[cite: 2]
    prompt = f"""
    You are a Senior Network Security Expert. 
    Our AI system detected a network anomaly with these features:
    {anomaly_data}
    
    Please provide:
    1. The likely type of attack.
    2. A brief explanation of the risk.
    3. A specific Cisco IOS Access Control List (ACL) command to mitigate this.
    """
    
    try:
        response = ollama.chat(model='llama3', messages=[
            {'role': 'user', 'content': prompt},
        ])
        return response['message']['content']
    except Exception as e:
        return f"❌ Failed to get advice from Llama 3: {str(e)}"

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🛡️  NETPULSE-SHIELD: ADVANCED AI REMEDIATION")
    print("="*50)

    # Étape de sécurité : On ne lance rien si Ollama est éteint
    if not check_ollama_status():
        sys.exit(1)

    # Simulation d'un scénario de charge élevée[cite: 2]
    test_anomaly = "Sload: 1,500,000,000, sttl: 254, sbytes: 5000"
    
    advice = get_security_advice(test_anomaly)
    print("\n" + advice)
    print("\n✅ Report generated successfully.")