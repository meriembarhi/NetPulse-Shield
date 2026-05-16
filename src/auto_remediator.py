import pandas as pd
import ollama

def generate_report():
    # 1. Load the alerts found by the detector
    try:
        alerts = pd.read_csv('alerts.csv')
    except FileNotFoundError:
        print("No alerts.csv found. Run detector.py first!")
        return

    report_content = "=== NETPULSE-SHIELD: AUTOMATED SECURITY REPORT ===\n\n"

    # 2. Process the top 3 most critical threats
    for index, row in alerts.head(3).iterrows():
        threat_data = f"Sload: {row['Sload']}, sttl: {row['sttl']}, sbytes: {row['sbytes']}"
        
        print(f" AI is analyzing Threat #{index+1}...")
        
        prompt = f"Analyze this network threat: {threat_data}. Give me the attack type and one Cisco ACL command to block it."
        
        response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}])
        
        report_content += f"THREAT #{index+1} ANALYSIS:\n"
        report_content += f"Data: {threat_data}\n"
        report_content += f"AI Response: {response['message']['content']}\n"
        report_content += "-"*40 + "\n"

    # 3. Save the final report
    with open('Security_Report.txt', 'w') as f:
        f.write(report_content)
    
    print("\n Success! Your professional report is ready: Security_Report.txt")

generate_report()