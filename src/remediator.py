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
    """Vrifie si le serveur Ollama est actif avant de lancer l'analyse.[cite: 2]"""
    try:
        # Le port par dfaut d'Ollama est 11434[cite: 2]
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        print(" Error: Ollama is not running.")
        print(" Please start Ollama or run 'ollama serve' in your terminal.")
        return False

def get_security_advice(anomaly_data):
    """Interroge Llama 3 pour obtenir un diagnostic structur et des commandes Cisco.[cite: 2]"""
    print(" Analyzing anomaly data with Llama 3...")
    
    # Updated Prompt: Forces categorization and professional formatting to avoid vague responses.
    prompt = f"""
    You are a Senior Network Security Expert. 
    Our AI system detected a network anomaly with these features:
    {anomaly_data}
    
    Provide a structured security report using exactly this format:
    
    1.  ATTACK TYPE: (Identify the specific attack, e.g., DoS, Port Scan, Exploits)
    2.  RISK LEVEL: (Low, Medium, High, or Critical)
    3.  TECHNICAL ANALYSIS: (Explain why these features suggest a threat)
    4.  MITIGATION STEPS: (Provide the exact Cisco IOS Access Control List (ACL) commands to block this)
    
    Ensure the advice is concrete and technically accurate for a Cisco environment.
    """
    
    try:
        response = ollama.chat(model='llama3', messages=[
            {'role': 'user', 'content': prompt},
        ])
        return response['message']['content']
    except Exception as e:
        return f" Failed to get advice from Llama 3: {str(e)}"

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  NETPULSE-SHIELD: ADVANCED AI REMEDIATION")
    print("="*60)

    # tape de scurit : On ne lance rien si Ollama est teint[cite: 2]
    if not check_ollama_status():
        sys.exit(1)

    # Simulation d'un scnario de charge leve (Example anomaly)[cite: 2]
    test_anomaly = "Sload: 1,500,000,000, sttl: 254, sbytes: 5000"
    
    advice = get_security_advice(test_anomaly)
    print("\n" + advice)
    print("\n" + "="*60)
    print(" Report generated successfully.")