import os
import json
import requests
import random
import logging
from pathlib import Path
import sys
from typing import Dict, List, Optional

# Setup absolute paths
PROJECT_ROOT = Path("/home/saus/crypto-crew-4.0")
POPULATION_FILE = PROJECT_ROOT / "user_data/strategies/population.json"
LOG_FILE = PROJECT_ROOT / "user_data/logs/ai_fixer.log"
DEEP_LOG_FILE = PROJECT_ROOT / "user_data/logs/ai_fixer_detailed.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, mode='a'), logging.StreamHandler()]
)

def deep_log(tag: str, data: str):
    """Log everything deeply to keep track of what AI is doing."""
    with open(DEEP_LOG_FILE, 'a') as f:
        f.write(f"\n[{tag}] =========================================\n")
        f.write(data)
        f.write(f"\n==================================================\n")

class AIGenomeFixer:
    def __init__(self):
        # Using local Ollama instead of OpenRouter
        self.active = True
        self.api_url = "http://localhost:11434/v1/chat/completions"
        self.model = "qwen2.5-coder:1.5b"
        logging.info(f"AI Fixer initialized with local Ollama ({self.model}).")

    def fix_genome(self, genome: Dict) -> Optional[Dict]:
        if not self.active: return None
        
        prompt = f"""You are an expert crypto quant. We have a Genetic Programming (GP) genome for Freqtrade that returns 0 trades.
The genome is a JSON AST. Your task is to modify the 'entry_tree' to be more inclusive (easier to trigger) or more logical, while keeping the EXACT SAME structure.

Current Genome:
{json.dumps(genome, indent=2)}

Rules for fixing:
1. Return ONLY the valid JSON of the fixed genome. No markdown, no explanations, no backticks.
2. Keep "primitive", "parameters", "operator", "children", "left", "right" keys EXACTLY as they are.
3. Common fix: Change LESS_THAN constant to a higher value, or change AND to OR.
4. Output nothing but raw JSON.
"""

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }

        deep_log("AI_PROMPT", prompt)

        try:
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            deep_log("AI_RAW_RESPONSE", content)
            
            # Extract JSON if LLM added markdown despite instructions
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            fixed_genome = json.loads(content.strip())
            deep_log("AI_PARSED_JSON", json.dumps(fixed_genome, indent=2))
            return fixed_genome
            
        except Exception as e:
            logging.error(f"AI Fix failed: {e}")
            deep_log("AI_ERROR", str(e))
            return None

    def process_population(self):
        if not POPULATION_FILE.exists():
            logging.warning("No population file found to fix.")
            return

        with open(POPULATION_FILE, 'r') as f:
            data = json.load(f)
        
        population = data.get("individuals", [])
        fixed_count = 0
        
        # Only fix the worst performers (fitness <= 0.0)
        for ind in population:
            # We check if fitness is exactly 0.0 or the default -0.007 we were seeing
            if (ind.get("fitness", 0) <= 0.0) and random.random() < 0.3: # Fix 30% of zero-performers
                logging.info("Attempting AI fix for zero-performing individual...")
                fixed = self.fix_genome(ind)
                if fixed and isinstance(fixed, dict) and "entry_tree" in fixed:
                    ind["entry_tree"] = fixed.get("entry_tree", ind["entry_tree"])
                    ind["exit_tree"] = fixed.get("exit_tree", ind["exit_tree"])
                    ind["fitness"] = -1.0 # Force re-evaluation
                    ind["ai_fixed"] = True # Flag to track LLM success
                    fixed_count += 1
        
        if fixed_count > 0:
            with open(POPULATION_FILE, 'w') as f:
                json.dump({"individuals": population}, f, indent=2)
            logging.info(f"Successfully fixed {fixed_count} individuals using AI.")
        else:
            logging.info("No AI fixes applied this round.")

if __name__ == "__main__":
    fixer = AIGenomeFixer()
    fixer.process_population()
