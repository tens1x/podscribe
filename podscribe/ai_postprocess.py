import os
import requests


def postprocess_text(raw_text: str) -> str:
    """Use Qwen LLM to clean up transcript: fix punctuation, add paragraphs."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return raw_text

    resp = requests.post(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "qwen-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a transcript editor. "
                        "Clean up the following speech-to-text transcript: "
                        "fix punctuation, remove filler words (嗯、啊、那个), "
                        "split into logical paragraphs, "
                        "but do NOT change the meaning or language. "
                        "Do NOT add any commentary, just output the cleaned text."
                    ),
                },
                {"role": "user", "content": raw_text},
            ],
        },
        timeout=120,
    )

    if resp.status_code != 200:
        return raw_text

    data = resp.json()
    return data["choices"][0]["message"]["content"]
