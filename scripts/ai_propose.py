#!/usr/bin/env python3
"""
AI Architect: Generate new trading strategy blocks using DeepSeek API.
"""
import os
import json
import ast
import requests
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple
import time

# Add project root to path to import PathResolver
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.paths import PathResolver

class AIArchitect:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
        
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        self.project_root = PathResolver.get_project_root()
        self.blocks_dir = self.project_root / "user_data" / "strategies" / "blocks"
        self.league_path = self.project_root / "user_data" / "strategies" / "league.json"
        self.dna_path = self.project_root / "user_data" / "strategies" / "dna.json"
        
        # Load example blocks to understand the pattern
        self.example_blocks = self._load_example_blocks()
        
    def _load_example_blocks(self) -> Dict[str, str]:
        """Load example blocks to use as templates for the AI."""
        examples = {}
        example_files = ["rsi_simple.py", "macd_simple.py"]
        for file_name in example_files:
            file_path = self.blocks_dir / file_name
            if file_path.exists():
                with open(file_path, 'r') as f:
                    examples[file_name] = f.read()
        return examples
    
    def _load_league(self) -> Dict:
        """Load league.json to understand which slots need attention."""
        if not self.league_path.exists():
            raise FileNotFoundError(f"league.json not found at {self.league_path}")
        with open(self.league_path, 'r') as f:
            return json.load(f)
    
    def _load_dna(self) -> Dict:
        """Load current dna.json."""
        if not self.dna_path.exists():
            raise FileNotFoundError(f"dna.json not found at {self.dna_path}")
        with open(self.dna_path, 'r') as f:
            return json.load(f)
    
    def _save_dna(self, dna_data: Dict) -> None:
        """Save dna.json."""
        with open(self.dna_path, 'w') as f:
            json.dump(dna_data, f, indent=2)
    
    def _validate_python_code(self, code: str) -> bool:
        """Validate Python code using ast.parse."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _call_deepseek_api(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Call DeepSeek API and return the response content."""
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Failed to parse API response: {e}")
            return None
    
    def generate_new_block(self, block_name: str, concept: str) -> Optional[str]:
        """Generate a completely new block with unique logic."""
        examples_text = "\n\n".join([f"File: {name}\n{content}" for name, content in self.example_blocks.items()])
        
        system_prompt = """You are an expert Python developer creating trading strategy blocks for freqtrade.
Each block must contain three functions:
1. populate_indicators(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame
2. populate_entry_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame
3. populate_exit_trend(dataframe: DataFrame, metadata: dict, params: dict) -> DataFrame

The block should be self-contained and follow the exact pattern of the examples.
Use pandas_ta for technical indicators.
Include parameters in the params dict with default values.
Only use 'enter_long' and 'exit_long' columns for signals.
"""
        
        user_prompt = f"""Create a new trading strategy block named '{block_name}.py' that implements {concept}.
The block should be unique and not just a copy of the examples.
Make sure to include appropriate parameters with sensible defaults.
Return only the Python code, no explanations or markdown formatting.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here are example blocks:\n\n{examples_text}\n\n{user_prompt}"}
        ]
        
        code = self._call_deepseek_api(messages)
        if code and self._validate_python_code(code):
            return code
        return None
    
    def tweak_existing_block(self, block_name: str, improvements: str) -> Optional[str]:
        """Tweak an existing block to make it safer."""
        # Load the existing block
        block_path = self.blocks_dir / f"{block_name}.py"
        if not block_path.exists():
            print(f"Block {block_name}.py does not exist")
            return None
        
        with open(block_path, 'r') as f:
            existing_code = f.read()
        
        system_prompt = """You are an expert Python developer improving trading strategy blocks for freqtrade.
Make the existing code safer by adding risk management, improving conditions, or adding filters.
Do not change the function signatures.
Keep the same overall logic but make it more robust.
"""
        
        user_prompt = f"""Here is the existing code for {block_name}.py:

{existing_code}

Improve this code to make it safer by: {improvements}
Return only the improved Python code, no explanations or markdown formatting.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        code = self._call_deepseek_api(messages)
        if code and self._validate_python_code(code):
            return code
        return None
    
    def process_league(self) -> None:
        """Process league.json to generate or tweak blocks."""
        league = self._load_league()
        
        # Load current DNA
        dna = self._load_dna()
        active_blocks = set(dna.get("active_blocks", []))
        
        # Process outsider slots (generate new blocks)
        outsiders = league.get("outsider_slots", [])
        for slot in outsiders:
            block_name = slot.get("name", f"block_{int(time.time())}")
            concept = slot.get("concept", "a unique trading indicator")
            
            print(f"Generating new block: {block_name} with concept: {concept}")
            code = self.generate_new_block(block_name, concept)
            if code:
                # Save the new block
                block_path = self.blocks_dir / f"{block_name}.py"
                with open(block_path, 'w') as f:
                    f.write(code)
                print(f"Saved new block to {block_path}")
                
                # Add to active blocks for testing
                active_blocks.add(block_name)
            else:
                print(f"Failed to generate valid code for {block_name}")
        
        # Process promising slots (tweak existing blocks)
        promising = league.get("promising_slots", [])
        for slot in promising:
            block_name = slot.get("block_name")
            improvements = slot.get("improvements", "make it safer")
            
            if not block_name:
                continue
                
            print(f"Tweaking existing block: {block_name} with improvements: {improvements}")
            code = self.tweak_existing_block(block_name, improvements)
            if code:
                # Save the tweaked block
                block_path = self.blocks_dir / f"{block_name}_tweaked.py"
                with open(block_path, 'w') as f:
                    f.write(code)
                print(f"Saved tweaked block to {block_path}")
                
                # Add to active blocks for testing
                active_blocks.add(f"{block_name}_tweaked")
            else:
                print(f"Failed to generate valid tweaked code for {block_name}")
        
        # Update DNA with new active blocks
        dna["active_blocks"] = list(active_blocks)
        self._save_dna(dna)
        print("Updated dna.json with new active blocks")

def main():
    """Main entry point."""
    try:
        architect = AIArchitect()
        architect.process_league()
        print("AI Architect completed successfully")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
