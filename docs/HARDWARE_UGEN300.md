# Hardware and honest validation
## Correct target
ASUS UGen300 uses Hailo-10H, up to 40 TOPS INT4 / 20 TOPS INT8.
Do not identify it as Hailo-8 26 TOPS.
Official specifications: https://www.asus.com/me-en/motherboards-components/ai-accelerator/ugen/ugen300-usb-8g/

## Current implementation
The real development backend is local Ollama with Qwen3 4B.
The development PC reports NVIDIA RTX 4050 Laptop GPU with approximately 6GB VRAM.
A CPU/GPU local run is not an NPU benchmark. No wattage or NPU latency is fabricated.
The old sleep-based simulator and claims of 28.4ms / 98.8% F1 have been removed.

## UGen300 transition
1. Obtain the actual kit or the organizer's official SDV environment.
2. Install the matching HailoRT and Hailo GenAI runtime.
3. Use an officially supported compiled model, initially Qwen3-1.7B-Instruct.
4. Start Hailo-Ollama, then set backend=hailo, endpoint=http://127.0.0.1:8000,
   and the model identifier reported by that runtime. Do not assume an Ollama GGUF is portable.
5. Run the same extraction dataset and end-to-end scheduling checks on the kit.
6. Record actual loading latency, extraction accuracy, generation latency, memory and measured power.
   Leave unavailable metrics blank.

Hailo model page: https://hailo.ai/products/hailo-software/model-explorer/generative-ai/qwen3-1-7b-instruct/
It lists context length 2048; trim input/context for that runtime.
Runtime: https://github.com/hailo-ai/hailo_model_zoo_genai
The application Hailo adapter validates returned JSON but does not assume Ollama JSON-schema support.
Status: adapter prepared, physical hardware and official SDV integration NOT validated.
