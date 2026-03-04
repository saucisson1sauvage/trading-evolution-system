from llama_cpp import Llama
import os
import json
import threading
import sys

# SUPPRESS LLAMA-CPP-PYTHON LOGS
os.environ['LLAMA_LOG_LEVEL'] = 'error'

MODEL_DIR = "/home/saus/crypto_crew/models"

class LocalLLM:
    def __init__(self, model_path, n_ctx=8192, lock=None, gpu_layers=30):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=1, # Single thread to respect the 6-thread limit
            n_gpu_layers=gpu_layers, 
            verbose=False
        )
        self.lock = lock

    def ask(self, system_prompt, user_prompt):
        if self.lock:
            with self.lock:
                return self._ask(system_prompt, user_prompt)
        return self._ask(system_prompt, user_prompt)

    def _ask(self, system_prompt, user_prompt):
        prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{user_prompt}<|end|>\n<|assistant|>\n"
        output = self.llm(prompt, max_tokens=2048, stop=["<|end|>"], echo=False)
        return output['choices'][0]['text'].strip()

class Crew:
    def __init__(self):
        # Global lock to prevent GPU conflicts
        self.gpu_lock = threading.Lock()
        
        # BRAIN stays on GPU for speed
        self.brain = LocalLLM(f"{MODEL_DIR}/brain.gguf", gpu_layers=30, lock=self.gpu_lock)
        
        # CODER moves to CPU to prevent "double free or corruption" crashes
        self.coder_llm = LocalLLM(f"{MODEL_DIR}/coder.gguf", n_ctx=8192, gpu_layers=0, lock=self.gpu_lock)

    def director(self, history_summary):
        sys = "DIRECTOR_MODE: Define the next evolution of the strategy. Be creative."
        return self.brain.ask(sys, f"HISTORY: {history_summary}\nCMD: Define target mutation.")

    def data_analyst(self, metrics_json):
        sys = "ANALYST_MODE: Identify why the strategy is failing or where it can improve."
        return self.brain.ask(sys, f"METRICS: {metrics_json}\nCMD: Output bottleneck.")

    def creative(self, analyst_feedback, vibe):
        sys = "STRATEGIST_MODE: Propose a brand new technical approach to trading."
        return self.brain.ask(sys, f"FEEDBACK: {analyst_feedback}. VIBE: {vibe}\nCMD: Propose fix.")

    def system_doctor(self, log_tail):
        sys = "DOCTOR_MODE: Diagnosis. Keywords: RESTART, REVERT_STRATEGY. Output only one word."
        return self.brain.ask(sys, f"LOGS: {log_tail}\nCMD: Diagnose.")

    def emergency_fixer(self, error_msg, broken_code):
        sys = "FIXER_MODE: Fix Python syntax errors. Output ONLY code."
        return self.coder_llm.ask(sys, f"ERROR: {error_msg}\nCODE: {broken_code}\nCMD: Fix.")

    def coder(self, strategy_code, creative_idea):
        sys = "CODER_MODE: Generate brand new strategy logic. Use dataframe.loc. Output ONLY code snippet."
        return self.coder_llm.ask(sys, f"STRAT: {strategy_code}\nIDEA: {creative_idea}\nCMD: Generate replacement logic.")
