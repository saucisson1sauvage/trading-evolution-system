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

# Load .env
if (PROJECT_ROOT / ".env").exists():
    with open(PROJECT_ROOT / ".env") as f:
        for line in f:
            if '=' in line:
                parts = line.strip().split('=', 1)
                if len(parts) == 2:
                    os.environ[parts[0]] = parts[1]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, mode='a'), logging.StreamHandler()]
)

class AIGenomeFixer:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            logging.error("OPENROUTER_API_KEY not found in .env or environment. Skipping AI fixes.")
            self.active = False
        else:
            self.active = True
            logging.info("AI Fixer initialized with OpenRouter API Key.")
        
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "google/gemini-2.0-flash-exp:free"

    def fix_genome(self, genome: Dict) -> Optional[Dict]:
        if not self.active: return None
        
        prompt = f"""You are an expert crypto quant. We have a Genetic Programming (GP) genome for Freqtrade that returns 0 trades.
The genome is a JSON AST. Your task is to modify the 'entry_tree' to be more inclusive (easier to trigger) or more logical, while keeping the structure.

Current Genome:
{json.dumps(genome, indent=2)}

Rules for fixing:
1. Return ONLY the valid JSON of the fixed genome.
2. Ensure you keep "primitive", "parameters", "operator", "children", "left", "right" keys exactly as they are.
3. Common fix: If it's a "LESS_THAN" with a very low constant, increase the constant. If it's an "AND", maybe change it to "OR".
4. Do not add markdown formatting or explanation.
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/freqtrade/freqtrade",
            "X-Title": "Crypto-Crew AI Fixer"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            # Extract JSON if LLM added markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            fixed_genome = json.loads(content.strip())
            return fixed_genome
        except Exception as e:
            logging.error(f"AI Fix failed: {e}")
            return None

    def process_population(self):
        if not POPULATION_FILE.exists():
            logging.warning("No population file found to fix.")
            return

        with open(POPULATION_FILE, 'r') as f:
            data = json.load(f)
        
        population = data.get("individuals", [])
        fixed_count = 0
        
        # Only fix the worst performers (fitness 0.0)
        for ind in population:
            if ind.get("fitness") == 0.0 and random.random() < 0.3: # Fix 30% of zero-performers
                logging.info("Attempting AI fix for zero-performing individual...")
                fixed = self.fix_genome(ind)
                if fixed:
                    ind["entry_tree"] = fixed.get("entry_tree", ind["entry_tree"])
                    ind["exit_tree"] = fixed.get("exit_tree", ind["exit_tree"])
                    ind["fitness"] = -1.0 # Force re-evaluation
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
