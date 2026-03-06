#!/usr/bin/env python3
"""
AI Architect: Generate new trading strategy genomes using OpenRouter API.
Verified by the Omniscience Gatekeeper.
"""
import os
import json
import requests
import random
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple
import time
import subprocess

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.gatekeeper import is_tungsten_safe
from user_data.strategies.gp_blocks import BLOCK_REGISTRY

class AIGenomeProposer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            # Fallback to local Ollama if OpenRouter key is missing
            self.api_url = "http://localhost:11434/v1/chat/completions"
            self.model = "qwen2.5-coder:1.5b"
            self.use_ollama = True
            print("Using local Ollama for genome generation.")
        else:
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"
            self.model = "google/gemini-2.0-flash-exp:free"
            self.use_ollama = False
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/freqtrade/freqtrade",
                "X-Title": "Crypto-Crew Proposer"
            }
        
        self.genomes_dir = PROJECT_ROOT / "user_data" / "strategies" / "genomes"
        self.hof_file = PROJECT_ROOT / "user_data" / "logs" / "ai_success_hall_of_fame.log"

    def _get_hof_context(self) -> str:
        examples = []
        if self.hof_file.exists():
            try:
                with open(self.hof_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        selected = random.sample(lines, min(len(lines), 2))
                        for line in selected:
                            data = json.loads(line)
                            examples.append(json.dumps(data["genome"], indent=2))
            except: pass
        return "\n---\n".join(examples)

    def propose_genome(self) -> Optional[Dict]:
        hof_context = self._get_hof_context()
        
        valid_nums = list(BLOCK_REGISTRY['num'].keys())
        valid_helpers = list(BLOCK_REGISTRY['bool_helper'].keys())
        valid_comps = list(BLOCK_REGISTRY['comparator'].keys())
        valid_ops = list(BLOCK_REGISTRY['operator'].keys())

        system_prompt = f"""You are a master quant architect. You design Freqtrade trading strategies using a JSON AST (Genome).
WARNING: Your output will be vetted by a 'Tungsten Guard' (Pytest/Inference). Hallucinated blocks will result in immediate rejection.

### AVAILABLE BLOCKS (PRIMITIVES):
- NUMERIC: {valid_nums}
- BOOLEAN HELPERS: {valid_helpers}
- COMPARATORS: {valid_comps}
- OPERATORS: {valid_ops}

### RULES:
1. Return ONLY valid JSON. No markdown, no explanations.
2. Structure: {{"entry_tree": {{...}}, "exit_tree": {{...}}}}
3. Every "primitive" MUST be from the list above.
4. "parameters" must be valid for the block (e.g., "window", "std", "threshold").
5. Logic must be nested using "operator" (AND, OR, NOT) with "children" array, or "primitive" (Comparators) with "left" and "right".
"""

        user_prompt = f"""Propose a sophisticated, profitable strategy genome.
{f"Examples of successful logic:\n{hof_context}" if hof_context else ""}

Focus on combining momentum (RSI) with volatility (Bollinger) and trend (EMA).
Output raw JSON only.
"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8
        }

        try:
            if self.use_ollama:
                response = requests.post(self.api_url, json=payload, timeout=60)
            else:
                response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)
            
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except Exception as e:
            print(f"Generation Error: {e}")
            return None

    def run(self):
        print("🚀 Proposing new genome...")
        genome = self.propose_genome()
        if not genome:
            return

        temp_path = PROJECT_ROOT / "user_data" / "temp_propose.json"
        with open(temp_path, 'w') as f:
            json.dump(genome, f, indent=2)

        if is_tungsten_safe(temp_path):
            print("✅ VERIFIED TUNGSTEN SOLID")
            timestamp = int(time.time())
            final_path = self.genomes_dir / f"ai_proposed_{timestamp}.json"
            temp_path.rename(final_path)
            
            # Git commit
            try:
                subprocess.run(["git", "add", str(final_path)], cwd=str(PROJECT_ROOT))
                subprocess.run(["git", "commit", "-m", f"Add AI-proposed genome: {final_path.name}"], cwd=str(PROJECT_ROOT))
                print(f"Archived and committed: {final_path.name}")
            except:
                print("Git commit failed (non-critical).")
        else:
            print("❌ REJECTED BY OMNISCIENCE")
            if temp_path.exists():
                temp_path.unlink()

if __name__ == "__main__":
    proposer = AIGenomeProposer()
    proposer.run()
