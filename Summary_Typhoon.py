from openai import OpenAI

client = OpenAI(
    api_key="sk-v6lYt8MFfKrqtCaTDbwAR3AjEDjZQQjM90uOZ2gMAjtdkdeh",
    base_url="https://api.opentyphoon.ai/v1"
)

messages = [
    {"role": "system", "content": "You are a professional analyst and technical writer.\n\nAnalyze the provided content and create a structured summary that is easy for busy readers to understand in less than 2 minutes.\n\nRequirements:\n\n1. Start with a 3-5 bullet executive summary.\n2. Group related information into logical sections.\n3. Use concise bullet points instead of long paragraphs whenever possible.\n4. Highlight important decisions, requirements, constraints, and assumptions.\n5. Identify action items and next steps.\n6. Identify missing information, risks, or unresolved issues.\n7. Use Markdown formatting for readability.\n8. If the content is technical, explain complex concepts in simple language.\n\nFocus on clarity, readability, and actionable insights rather than simply shortening the text.\n"},
    {"role": "user", "content": "input text here: " + input()}
]

stream = client.chat.completions.create(
    model="typhoon-v2.5-30b-a3b-instruct",
    messages=messages,
    temperature=0.6,
    max_completion_tokens=512,
    top_p=0.6,
    frequency_penalty=0,
    stream=True
)

# Process the streaming response
for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()  # Add a newline at the end