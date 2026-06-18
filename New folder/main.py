import os, csv, re, time, requests
import numpy as np
from pathlib import Path
import pandas as pd
import json

THAILLM_API_KEY = "ou9erMIcBaSv0QwU9ExnIK7B1CiAJ9u0"




def ask_llm(messages, model="typhoon", max_retries=5):
    """Call ThaiLLM API with retry and rate-limit handling.

    Available models: typhoon, openthaigpt, pathumma, kbtg
    """
    url = f"http://thaillm.or.th/api/{model}/v1/chat/completions"
    headers = {"Content-Type": "application/json", "apikey": THAILLM_API_KEY}
    payload = {
        "model": "/model",
        "messages": messages,
        "max_tokens": 2024,
        "temperature": 0,

        # ลองตัวนี้ก่อน ถ้า backend เป็น vLLM/Qwen compatible
        "chat_template_kwargs": {
            "enable_thinking": False
        }
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    return resp

ans = ask_llm([{"role":"user","content":"hello world"}])
print(ans.json()['choices'][0]['message']['content'])