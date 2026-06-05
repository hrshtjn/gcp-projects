import os
from dotenv import load_dotenv

# We must load .env first so GOOGLE_APPLICATION_CREDENTIALS is set 
# before any Google Cloud libraries are imported or initialized.
load_dotenv()

import vertexai
from vertexai.generative_models import GenerativeModel

def main():
    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    
    if not project_id:
        print("Please set GCP_PROJECT_ID in your .env file.")
        return

    print(f"Initializing Vertex AI in project '{project_id}' and location '{location}'...")
    
    # GCP libraries automatically look for GOOGLE_APPLICATION_CREDENTIALS.
    # The JSON config tells it to exchange the token in `keycloak_token.txt` for GCP credentials.
    vertexai.init(project=project_id, location=location)

    # Note: Using gemini-1.5-flash-001 or gemini-1.5-pro-preview-0409 based on your requirement
    model_name = "gemini-2.5-flash"
    print(f"Loading model {model_name}...")
    model = GenerativeModel(model_name)
    
    prompt = "Explain why Workload Identity Federation is more secure than Service Account JSON keys, in 2 concise sentences."
    print(f"Calling Gemini with prompt: '{prompt}'\n")
    
    response = model.generate_content(prompt)
    
    print("--- Gemini Response ---")
    print(response.text)

if __name__ == "__main__":
    main()