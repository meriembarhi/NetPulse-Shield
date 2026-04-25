import ollama

def get_security_advice(anomaly_data):
    print(f"Analyzing anomaly data with Llama3...")
    
    # This prompt tells the AI exactly how to behave
    prompt = f"""
    You are a Senior Network Security Expert. 
    Our AI system detected a network anomaly with these features:
    {anomaly_data}
    
    Please provide:
    1. The likely type of attack.
    2. A brief explanation of the risk.
    3. A specific Cisco IOS Access Control List (ACL) command to mitigate this.
    """
    
    response = ollama.chat(model='llama3', messages=[
        {'role': 'user', 'content': prompt},
    ])
    
    return response['message']['content']

# Testing with a high-load scenario
test_anomaly = "Sload: 1,500,000,000, sttl: 254, sbytes: 5000"
print("\n" + "="*40)
print("NETPULSE-SHIELD: AI REMEDIATION REPORT")
print("="*40)
print(get_security_advice(test_anomaly))