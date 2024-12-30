import json
import os
import re
import requests
from dotenv import load_dotenv
from exa_py import Exa
import openai
from openai import OpenAI
import instructor
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()
exa_labs_api_key = os.getenv("exa_labs")
openai.api_key = os.getenv("OPENAI_API_KEY")

class PromptGen(BaseModel):
    prompt: str = Field(description="A prompt for a search query based on the system prompt")

# Initialize OpenAI client
api_key = os.getenv('open_ai')
instructor_client = instructor.patch(OpenAI(api_key=api_key))

# Function to generate keywords based on a given topic
def generate_prompt(topic: str) -> PromptGen:
    response = instructor_client.chat.completions.create(
        model="gpt-4o",
        response_model=PromptGen,
        messages=[
            {
                "role": "system", 
                "content": """You are an expert in cybersecurity and financial services tasked with generating a specialized search query. 
                Given a topic, create a focused query that: 
                1) Targets authoritative sources and regulatory guidance specific to that topic, 
                2) Emphasizes cybersecurity frameworks and standards relevant to financial institutions, 
                3) Prioritizes content from recognized regulatory bodies and industry leaders in that domain, and 
                4) Ensures the query captures the intersection of the topic with risk management and compliance requirements."""
            },
            {
                "role": "user",
                "content": f"Here is the topic: {topic}"
            }
        ]
    )
    
    return response.prompt

topics = ["Asset Management", "AI", "Identity", "Marketing", "Privledge Access Management"]
prompts = [generate_prompt(topic) for topic in topics]
# Save prompts to a text file
os.makedirs('outputs', exist_ok=True)

prompts_file_path = os.path.join('outputs', 'generated_prompts.txt')
with open(prompts_file_path, 'w') as f:
    for topic, prompt in zip(topics, prompts):
        f.write(f"Topic: {topic}\n")
        f.write(f"Generated Prompt: {prompt}\n")
        f.write("-" * 80 + "\n\n")




# Initialize Exa client
exa = Exa(api_key=exa_labs_api_key)

def get_prompt_from_file(topic):
    prompts_file_path = os.path.join('outputs', 'generated_prompts.txt')
    with open(prompts_file_path, 'r') as f:
        content = f.read()
    
    # Find the section for the given topic
    sections = content.split('-' * 80)
    for section in sections:
        if f"Topic: {topic}" in section:
            # Extract the prompt part
            prompt_line = [line for line in section.split('\n') if "Generated Prompt:" in line][0]
            return prompt_line.replace("Generated Prompt: ", "").strip()
    return None

def main(topic):
    # Create necessary directories at the start
    os.makedirs('outputs', exist_ok=True)
    
    # Get pre-generated query from file
    query = get_prompt_from_file(topic)
    if not query:
        print(f"No pre-generated prompt found for topic: {topic}")
        return
    
    print(f"Using query for {topic}: {query}")
    
    # Perform the search with the string query
    result = exa.search_and_contents(
        query=query,
        type="neural",
        use_autoprompt=True,
        category="pdf",
        highlights=True,
        start_published_date="2024-01-02T00:20:13.157Z",
        end_published_date="2024-12-15T00:20:13.157Z",
        start_crawl_date="2024-01-02T00:20:13.157Z",
        end_crawl_date="2024-12-15T00:20:13.157Z",
        num_results=10,
        summary={
            "query": "Make sure you include the PDF link inside the summary here if available"
        }
    )
    
    # Extract relevant data from the SearchResponse object
    serializable_results = [
        {
            "title": r.title,
            "url": r.url,
            "id": r.id,
            "score": r.score,
            "published_date": r.published_date,
            "author": r.author,
            "highlights": r.highlights,
            "summary": r.summary
        }
        for r in result.results
    ]

    # Create topic-specific directory
    topic_dir = os.path.join('outputs', topic.lower().replace(" ", "_"))
    os.makedirs(topic_dir, exist_ok=True)

    # Serialize the data to JSON with topic-specific filename
    json_results = json.dumps(serializable_results, indent=2)
    file_path = os.path.join(topic_dir, 'exa_labs_output.json')
    with open(file_path, 'w') as f:
        f.write(json_results)
    print(f"Results for {topic} saved to {file_path}")

# Process each topic separately
for topic in ["Asset Management", "AI", "Identity", "Marketing", "Privledge Access Management"]:
    main(topic)