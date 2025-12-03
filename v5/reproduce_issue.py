
import sys
import os
import json

# Add the current directory to sys.path to make app module importable
sys.path.append(os.getcwd())

from app.services.nlp_service import NLPService

def test_query(query):
    print(f"\nTesting Query: '{query}'")
    try:
        result = NLPService.analyze_query(query)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    query = input("Enter query: ")
    test_query(query)
