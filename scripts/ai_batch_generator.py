"""
AI Batch Generator for Genetic Strategy Evolution
Implements secure key loading, 30-minute strike system, and delimiter extraction.
"""
import json
import sys
import os
import time
import requests
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import BLOCK_REGISTRY from gp_blocks
try:
    # Since gp_blocks.py is in user_data/strategies/, we need to adjust the path
    gp_blocks_path = project_root / "user_data" / "strategies" / "gp_blocks.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location("gp_blocks", gp_blocks_path)
    gp_blocks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gp_blocks)
    BLOCK_REGISTRY = gp_blocks.BLOCK_REGISTRY
except Exception as e:
    print(f"Error: Could not import BLOCK_REGISTRY: {e}")
    sys.exit(1)

# 1. SMART KEY MANAGER
class KeyManager:
    """Manages API keys with rotation and cooldown for rate limiting"""
    def __init__(self, api_keys: List[str]):
        if len(api_keys) != 2:
            sys.exit("Error: Exactly 2 API keys are required for smart rotation")
        self.keys = api_keys
        self.cooldowns = {}  # key -> timestamp when cooldown ends
        self.cooldown_duration = 60  # seconds
        
    def get_available_key(self, current_gen: int) -> str:
        """Select a key based on generation parity, respecting cooldowns"""
        # Primary selection based on generation parity
        primary_index = current_gen % 2
        primary_key = self.keys[primary_index]
        
        # Check if primary key is in cooldown
        current_time = time.time()
        if primary_key in self.cooldowns:
            cooldown_end = self.cooldowns[primary_key]
            if current_time < cooldown_end:
                print(f"  Key {primary_index} is in cooldown (until {cooldown_end:.1f}s). Switching to alternate key.")
                # Use alternate key
                alternate_index = 1 - primary_index
                alternate_key = self.keys[alternate_index]
                
                # Check if alternate key is also in cooldown
                if alternate_key in self.cooldowns and current_time < self.cooldowns[alternate_key]:
                    print(f"  Both keys are in cooldown! Waiting for primary key...")
                    # Wait for primary key cooldown to end
                    wait_time = cooldown_end - current_time + 1
                    print(f"  Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    return primary_key
                return alternate_key
        
        print(f"  Using key {primary_index} (generation {current_gen} is {'even' if current_gen % 2 == 0 else 'odd'})")
        return primary_key
    
    def mark_cooldown(self, key: str):
        """Mark a key as being in cooldown due to rate limiting"""
        self.cooldowns[key] = time.time() + self.cooldown_duration
        key_index = self.keys.index(key)
        print(f"  Key {key_index} marked for cooldown for {self.cooldown_duration} seconds")
    
    def clear_expired_cooldowns(self):
        """Remove expired cooldown entries"""
        current_time = time.time()
        expired_keys = [k for k, end_time in self.cooldowns.items() if current_time >= end_time]
        for key in expired_keys:
            del self.cooldowns[key]
            key_index = self.keys.index(key)
            print(f"  Key {key_index} cooldown expired and cleared")

def load_api_keys() -> List[str]:
    """Load API keys from user_data/api_keys.json"""
    api_keys_path = project_root / "user_data" / "api_keys.json"
    if not api_keys_path.exists():
        sys.exit("Error: user_data/api_keys.json missing.")
    
    try:
        with open(api_keys_path, 'r') as f:
            data = json.load(f)
        api_keys = data.get("api_keys", [])
        if not api_keys:
            sys.exit("Error: No API keys found in api_keys.json")
        return api_keys
    except json.JSONDecodeError:
        sys.exit("Error: Invalid JSON in api_keys.json")
    except Exception as e:
        sys.exit(f"Error reading api_keys.json: {e}")

# 2. STRIKE SYSTEM
def check_strikes() -> None:
    """Check if we have too many recent strikes"""
    strikes_path = project_root / "user_data" / "logs" / "strikes.json"
    
    # Create directory if it doesn't exist
    strikes_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load or create strikes file
    if strikes_path.exists():
        try:
            with open(strikes_path, 'r') as f:
                strikes = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            strikes = []
    else:
        strikes = []
    
    # Filter out strikes older than 30 minutes (1800 seconds)
    current_time = time.time()
    recent_strikes = [s for s in strikes if current_time - s < 1800]
    
    # If we have 10 or more recent strikes, halt the engine
    if len(recent_strikes) >= 10:
        sys.exit("🚨 FATAL: 10 AI HALLUCINATION STRIKES IN 30 MINS. HALTING ENGINE. 🚨")
    
    # Save back only recent strikes
    if strikes != recent_strikes:
        with open(strikes_path, 'w') as f:
            json.dump(recent_strikes, f)

def add_strike() -> None:
    """Add a new strike timestamp"""
    strikes_path = project_root / "user_data" / "logs" / "strikes.json"
    
    # Load current strikes
    if strikes_path.exists():
        try:
            with open(strikes_path, 'r') as f:
                strikes = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            strikes = []
    else:
        strikes = []
    
    # Add current timestamp
    strikes.append(time.time())
    
    # Save back
    with open(strikes_path, 'w') as f:
        json.dump(strikes, f)

# 3. VALIDATION FUNCTIONS
def validate_tree_structure(node: Dict[str, Any]) -> bool:
    """Recursively validate tree structure and check primitives exist in BLOCK_REGISTRY"""
    # Check if node has 'primitive' key
    if 'primitive' in node:
        primitive_name = node['primitive']
        # Check if primitive exists in any category of BLOCK_REGISTRY
        found = False
        for category in BLOCK_REGISTRY.values():
            if primitive_name in category:
                found = True
                break
        if not found:
            print(f"  Validation error: Primitive '{primitive_name}' not found in BLOCK_REGISTRY")
            return False
        
        # Check parameters if present
        if 'parameters' in node:
            if not isinstance(node['parameters'], dict):
                print(f"  Validation error: Parameters must be a dict for primitive '{primitive_name}'")
                return False
        
        # Check left/right if present
        if 'left' in node:
            if not isinstance(node['left'], dict):
                print(f"  Validation error: 'left' must be a dict for primitive '{primitive_name}'")
                return False
            if not validate_tree_structure(node['left']):
                return False
        
        if 'right' in node:
            if not isinstance(node['right'], dict):
                print(f"  Validation error: 'right' must be a dict for primitive '{primitive_name}'")
                return False
            if not validate_tree_structure(node['right']):
                return False
        
        return True
    
    # Check if node has 'operator' key
    elif 'operator' in node:
        operator = node['operator']
        valid_operators = ['AND', 'OR', 'NOT']
        if operator not in valid_operators:
            print(f"  Validation error: Invalid operator '{operator}'")
            return False
        
        # Check children
        if 'children' in node:
            if not isinstance(node['children'], list):
                print(f"  Validation error: 'children' must be a list for operator '{operator}'")
                return False
            for child in node['children']:
                if not isinstance(child, dict):
                    print(f"  Validation error: Child must be a dict for operator '{operator}'")
                    return False
                if not validate_tree_structure(child):
                    return False
        else:
            print(f"  Validation error: Operator '{operator}' must have 'children' key")
            return False
        
        return True
    
    # Check for constant node
    elif 'constant' in node:
        # Constant can be a number
        if not isinstance(node['constant'], (int, float)):
            print(f"  Validation error: Constant must be a number, got {type(node['constant'])}")
            return False
        return True
    
    else:
        print(f"  Validation error: Node must have 'primitive', 'operator', or 'constant' key")
        return False

def validate_batch(batch: List[Dict[str, Any]]) -> bool:
    """Validate the entire batch of genomes"""
    # Check if batch is a list of 5 objects
    if not isinstance(batch, list):
        print("Validation error: Batch must be a list")
        return False
    
    if len(batch) != 5:
        print(f"Validation error: Batch must contain exactly 5 objects, got {len(batch)}")
        return False
    
    # Validate each object
    for i, obj in enumerate(batch):
        if not isinstance(obj, dict):
            print(f"Validation error: Object {i} must be a dict")
            return False
        
        # Check required keys
        required_keys = ['type', 'entry_tree', 'exit_tree']
        for key in required_keys:
            if key not in obj:
                print(f"Validation error: Object {i} missing key '{key}'")
                return False
        
        # Check type
        valid_types = ['mutated_rank_1', 'mutated_rank_2', 'guided_outsider', 
                      'alien_outsider_A', 'alien_outsider_B']
        if obj['type'] not in valid_types:
            print(f"Validation error: Object {i} has invalid type '{obj['type']}'")
            return False
        
        # Validate entry tree
        print(f"Validating entry tree for object {i} (type: {obj['type']})...")
        if not validate_tree_structure(obj['entry_tree']):
            print(f"  Failed to validate entry tree for object {i}")
            return False
        
        # Validate exit tree
        print(f"Validating exit tree for object {i} (type: {obj['type']})...")
        if not validate_tree_structure(obj['exit_tree']):
            print(f"  Failed to validate exit tree for object {i}")
            return False
    
    return True

# 4. API CALLER & EXTRACTOR
def call_gemini(api_key: str, model: str, system_prompt: str, user_prompt: str, key_manager: KeyManager = None) -> str:
    """Call Gemini API and return the response text with rate limit handling"""
    # Compress prompts to save tokens
    system_prompt = re.sub(r'\s+', ' ', system_prompt).strip()
    user_prompt = re.sub(r'\s+', ' ', user_prompt).strip()
    
    # Try up to 2 attempts (primary key + alternate key)
    for attempt in range(2):
        current_api_key = api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={current_api_key}"
        
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.7
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add pacing to prevent bursting the RPM limit
        time.sleep(4)
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # Extract text from response
            if 'candidates' in data and len(data['candidates']) > 0:
                candidate = data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    if len(parts) > 0 and 'text' in parts[0]:
                        return parts[0]['text']
            
            # If we couldn't extract text, raise an error
            raise ValueError("Could not extract text from API response")
            
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                status_code = e.response.status_code
                if status_code == 429:  # Rate limit exceeded
                    print(f"  Rate limit (429) hit for current API key (attempt {attempt + 1}/2)")
                    if key_manager is not None:
                        key_manager.mark_cooldown(current_api_key)
                        # Get alternate key for next attempt
                        if attempt == 0:
                            # Use current generation number or timestamp to get alternate key
                            # Since we don't have current_generation here, use timestamp
                            import time
                            api_key = key_manager.get_available_key(int(time.time()))
                            print(f"  Switching to alternate key for retry")
                            continue
                    # If we're on the last attempt or no key_manager, raise
                    if attempt == 1:
                        print(f"  Both keys failed with 429 errors")
                        raise
                    else:
                        # This shouldn't happen if key_manager is provided
                        raise
                else:
                    print(f"API request failed with status {status_code}: {e}")
                    print(f"Response body: {e.response.text[:200]}")
                    raise
            else:
                print(f"API request failed: {e}")
                raise
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            raise
        except (KeyError, ValueError) as e:
            print(f"Failed to parse API response: {e}")
            print(f"Response was: {data if 'data' in locals() else 'No data'}")
            raise
    
    # This should never be reached, but just in case
    raise RuntimeError("Unexpected error in call_gemini")

def extract_json(text: str) -> str:
    """Extract JSON between delimiters"""
    # Split by start delimiter
    parts = text.split("@@@JSON_START@@@")
    if len(parts) < 2:
        # Try to find JSON without delimiters (fallback)
        print("Warning: Start delimiter not found, trying to find JSON directly")
        # Look for the first '[' or '{' and last ']' or '}'
        start_idx = text.find('[')
        if start_idx == -1:
            start_idx = text.find('{')
        if start_idx == -1:
            raise ValueError("No JSON start found in response")
        
        # Find matching end
        # This is a simple approach - for proper parsing we'd need a JSON parser
        # But for now, we'll assume the JSON is at the end
        # Let's try to parse from start_idx
        json_candidate = text[start_idx:]
        # Try to validate it's valid JSON by parsing
        try:
            json.loads(json_candidate)
            return json_candidate
        except json.JSONDecodeError:
            # Try to find the end
            # Count brackets to find matching end
            pass
        
        raise ValueError("Could not extract valid JSON from response")
    
    # Split by end delimiter
    end_parts = parts[1].split("@@@JSON_END@@@")
    if len(end_parts) < 1:
        raise ValueError("End delimiter not found")
    
    json_part = end_parts[0].strip()
    if not json_part:
        raise ValueError("Empty content between delimiters")
    
    return json_part

# 5. MAIN FUNCTION
def main() -> None:
    """Main execution function"""
    print("AI Batch Generator - Starting...")
    
    # Load API keys
    print("1. Loading API keys...")
    api_keys = load_api_keys()
    print(f"   Loaded {len(api_keys)} API key(s)")
    
    # Load payload cache
    print("2. Loading AI payload cache...")
    cache_path = project_root / "user_data" / "logs" / "ai_payload_cache.json"
    if not cache_path.exists():
        # Try to run generate_ai_context.py first
        print(f"  Cache not found at {cache_path}")
        print("  Attempting to generate cache by running scripts/generate_ai_context.py...")
        generate_script = project_root / "scripts" / "generate_ai_context.py"
        if generate_script.exists():
            import subprocess
            try:
                result = subprocess.run([sys.executable, str(generate_script)], 
                                      capture_output=True, text=True, cwd=project_root)
                if result.returncode == 0:
                    print("  Cache generated successfully")
                else:
                    print(f"  Failed to generate cache: {result.stderr}")
                    sys.exit(1)
            except Exception as e:
                print(f"  Error running generate_ai_context.py: {e}")
                sys.exit(1)
        else:
            sys.exit(f"Error: {cache_path} not found and cannot generate cache")
    
    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
    except Exception as e:
        sys.exit(f"Error loading cache: {e}")
    
    static_anchor = cache_data.get("static_anchor", "")
    dynamic_tail = cache_data.get("dynamic_tail", "")
    current_generation = cache_data.get("current_generation", 0)
    
    if not static_anchor or not dynamic_tail:
        sys.exit("Error: Cache data is incomplete")
    
    print(f"   Generation: {current_generation}")
    
    # Initialize KeyManager
    key_manager = KeyManager(api_keys)
    
    # Clear any expired cooldowns before starting
    key_manager.clear_expired_cooldowns()
    
    # Model selection - Force use of gemini-3.1-flash-lite-preview only
    model = "gemini-3.1-flash-lite-preview"
    print(f"   Selected model: {model} (forced)")
    
    # Get key using smart rotation
    api_key = key_manager.get_available_key(current_generation)
    
    # Add custom delimiter instruction
    dynamic_tail += "\n\nCRITICAL INSTRUCTION: You MUST wrap your entire JSON array between the exact text @@@JSON_START@@@ and @@@JSON_END@@@. Do not output anything outside of these tags."
    
    # Combine prompts
    system_prompt = "You are an elite quantitative trading strategy generator. Follow all instructions precisely."
    user_prompt = static_anchor + "\n\n" + dynamic_tail
    
    # Main validation loop
    max_attempts = 3
    for attempt in range(max_attempts):
        print(f"\n--- Attempt {attempt + 1}/{max_attempts} ---")
        
        # Check strikes before each attempt
        check_strikes()
        
        try:
            # Call API
            print("3. Calling Gemini API...")
            response_text = call_gemini(api_key, model, system_prompt, user_prompt, key_manager)
            
            # Log AI transcript
            try:
                transcript_dir = project_root / "user_data" / "logs" / "ai_transcripts"
                transcript_dir.mkdir(parents=True, exist_ok=True)
                transcript_path = transcript_dir / f"gen_{current_generation}.json"
                transcript_data = {
                    "generation": current_generation,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "raw_response": response_text
                }
                with open(transcript_path, 'w') as f:
                    json.dump(transcript_data, f, indent=2)
                print(f"   AI transcript saved to {transcript_path}")
            except Exception as e:
                print(f"   Failed to save AI transcript: {e}")
            
            # Extract JSON
            print("4. Extracting JSON from response...")
            json_text = extract_json(response_text)
            
            # Parse JSON
            print("5. Parsing JSON...")
            batch = json.loads(json_text)
            
            # Validate batch
            print("6. Validating batch...")
            if validate_batch(batch):
                print("✓ Batch validation successful!")
                
                # Save to file
                output_path = project_root / "user_data" / "strategies" / "latest_ai_batch.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w') as f:
                    json.dump(batch, f, indent=2)
                
                print(f"✓ Batch saved to {output_path}")
                print("✓ AI Batch Generator completed successfully!")
                sys.exit(0)
            else:
                print("✗ Batch validation failed")
                raise ValueError("Batch validation failed")
                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            
            # Add strike for this failure
            add_strike()
            print("  Strike recorded")
            
            # Wait before retry (except on last attempt)
            if attempt < max_attempts - 1:
                print("  Waiting 5 seconds before retry...")
                time.sleep(5)
    
    # If we get here, all attempts failed
    print("\n✗ All attempts failed. Exiting.")
    sys.exit(1)

if __name__ == "__main__":
    main()
