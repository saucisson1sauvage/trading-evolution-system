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
HOF_FILE = PROJECT_ROOT / "user_data/logs/ai_success_hall_of_fame.log"
LOG_FILE = PROJECT_ROOT / "user_data/logs/ai_fixer.log"
DEEP_LOG_FILE = PROJECT_ROOT / "user_data/logs/ai_fixer_detailed.log"
AIDER_LOG_FILE = PROJECT_ROOT / "user_data/logs/aider_debug.log"

def log_aider(message: str):
    """Log high-signal events for Aider context."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(AIDER_LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    # Keep it light: only last 500 lines
    if AIDER_LOG_FILE.exists():
        with open(AIDER_LOG_FILE, 'r') as f:
            lines = f.readlines()
        if len(lines) > 500:
            with open(AIDER_LOG_FILE, 'w') as f:
                f.writelines(lines[-500:])

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
        self.active = True
        self.api_url = "http://localhost:11434/v1/chat/completions"
        self.model = "qwen2.5-coder:1.5b"
        self.hall_of_fame_examples = self._load_hall_of_fame()
        logging.info(f"AI Fixer initialized with local Ollama ({self.model}). Loaded {len(self.hall_of_fame_examples)} HOF examples.")

    def _load_hall_of_fame(self) -> List[str]:
        """Load the best performing AI-fixed genomes to use as examples."""
        examples = []
        if HOF_FILE.exists():
            try:
                with open(HOF_FILE, 'r') as f:
                    lines = f.readlines()
                    # Take up to 3 random high-performing examples
                    if lines:
                        selected_lines = random.sample(lines, min(len(lines), 3))
                        for line in selected_lines:
                            data = json.loads(line)
                            # Just keep the entry/exit logic to save context
                            logic_only = {
                                "entry_tree": data["genome"]["entry_tree"],
                                "exit_tree": data["genome"]["exit_tree"],
                                "profit": data.get("profit", "N/A")
                            }
                            examples.append(json.dumps(logic_only, indent=2))
            except Exception as e:
                logging.error(f"Failed to load Hall of Fame: {e}")
        return examples

    def fix_genome(self, genome: Dict) -> Optional[Dict]:
        if not self.active: return None
        
        hof_context = ""
        if self.hall_of_fame_examples:
            hof_context = "\n### EXAMPLES OF PREVIOUS SUCCESSFUL GENOMES (THAT MADE PROFIT):\n"
            hof_context += "\n---\n".join(self.hall_of_fame_examples)
            hof_context += "\n\n"

        prompt = f"""You are an expert crypto quant. We have a Genetic Programming (GP) genome for Freqtrade that returns 0 trades or is failing.
The genome is a JSON AST. Your task is to modify the 'entry_tree' to be more inclusive (easier to trigger) or more logical, while keeping the EXACT SAME structure.

### CRITICAL GOAL: INCREASE TRADE FREQUENCY
We want strategies that trigger MANY trades across the 6-month period. A strategy with only 1-2 "lucky" trades is considered a failure. 
Adjust constants and operators to ensure the strategy finds consistent entry points. 

{hof_context}
### CURRENT FAILED GENOME TO FIX:
{json.dumps(genome, indent=2)}

### RULES:
1. Return ONLY the valid JSON of the fixed genome. No markdown, no explanations, no backticks.
2. Keep "primitive", "parameters", "operator", "children", "left", "right" keys EXACTLY as they are.
3. Common fix: Change LESS_THAN constant to a higher value, change GREATER_THAN to a lower value, or change AND to OR.
4. Aim for logic that triggers at least 20-50 trades in 6 months.
5. Use the provided EXAMPLES to see what profitable, active logic looks like.
6. Output nothing but raw JSON.
"""

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4 # Slightly lower temp for more precision
        }

        deep_log("AI_PROMPT", prompt)

        try:
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            deep_log("AI_RAW_RESPONSE", content)
            
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
        
        for ind in population:
            # Fix if fitness is 0 (no trades) or very low/negative
            if (ind.get("fitness", 0) <= 0.0) and random.random() < 0.4:
                logging.info("Attempting AI fix for zero-performing individual...")
                fixed = self.fix_genome(ind)
                if fixed and isinstance(fixed, dict) and "entry_tree" in fixed:
                    ind["entry_tree"] = fixed.get("entry_tree", ind["entry_tree"])
                    ind["exit_tree"] = fixed.get("exit_tree", ind["exit_tree"])
                    ind["fitness"] = -1.0 
                    ind["ai_fixed"] = True
                    fixed_count += 1
        
        if fixed_count > 0:
            with open(POPULATION_FILE, 'w') as f:
                json.dump({"individuals": population}, f, indent=2)
            logging.info(f"Successfully fixed {fixed_count} individuals using AI.")
            log_aider(f"AI FIX applied to {fixed_count} individuals.")
        else:
            logging.info("No AI fixes applied this round.")

if __name__ == "__main__":
    fixer = AIGenomeFixer()
    fixer.process_population()
