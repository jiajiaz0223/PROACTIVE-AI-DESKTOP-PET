"""Real Hailo-Ollama adapter; physical UGen300 validation is outstanding."""
from proactive_pet.ai.local_model import LocalModel
class HailoBackend(LocalModel):
    def __init__(self, model='qwen3:1.7b', base_url='http://127.0.0.1:8000'):
        super().__init__(model, base_url, backend='hailo')
