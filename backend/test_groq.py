import os
from dotenv import load_dotenv
load_dotenv()
from groq import Groq

api_key = os.getenv("GROQ_API_KEY")
print(f"API Key found: {'YES' if api_key else 'NO'}")
print(f"Key starts with: {api_key[:8] if api_key else 'MISSING'}...")

client = Groq(api_key=api_key)

r = client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[{"role": "user", "content": 'Reply with only this exact JSON: {"risk_score":15,"summary":"test ok","findings":["groq working"]}'}],
    max_tokens=100
)

print("GROQ RESPONSE:", r.choices[0].message.content)
print("SUCCESS - Groq is working!")
