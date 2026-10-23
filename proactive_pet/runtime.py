"""Start the project-local Ollama service without changing global settings."""
import json
import os
from pathlib import Path
import subprocess
import urllib.request


def ensure_runtime(project):
    root = Path(project)
    endpoint = 'http://127.0.0.1:11435'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(endpoint + '/api/version', timeout=1) as response:
            return json.load(response)
    except Exception:
        pass
    exe = root / '.runtime' / 'ollama' / 'ollama.exe'
    if not exe.exists():
        return None
    env = os.environ.copy()
    env.update(OLLAMA_HOST='127.0.0.1:11435', OLLAMA_MODELS=str(root / '.runtime' / 'models'),
               OLLAMA_NO_CLOUD='1', OLLAMA_NUM_PARALLEL='1')
    logdir = root / 'data'
    logdir.mkdir(exist_ok=True)
    with (logdir / 'ollama.log').open('ab') as log:
        subprocess.Popen([str(exe), 'serve'], env=env, stdout=log, stderr=log,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), cwd=root)
    return {'starting': True}
