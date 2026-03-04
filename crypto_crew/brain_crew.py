import os
# Suppress torch warnings about CUDA capability
os.environ['TORCH_CPP_LOG_LEVEL'] = 'ERROR'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1' # Force CPU to stop compatibility spam

import torch
import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime

# --- CONFIG ---
VIBE_FILE = "/home/saus/crypto_crew/market_vibe.json"
IDEAS_FILE = "/home/saus/crypto_crew/creative_ideas.json"

class CreativeBrain:
    def __init__(self):
        print("[Brain] Initializing Creative Engine on CPU (Stability Mode)...")
        # Dummy model for idea generation
        self.model = torch.nn.Linear(10, 10)

    def brainstorm(self):
        """
        Generates 'Creative Hypotheses' for new strategy structures.
        """
        logics = ['trend_follower', 'mean_reversion', 'quick_scalp', 'vol_breakout']
        shorts = ['vortex_short', 'ema_rejection', 'exhaustion_short', 'none']
        
        idea = {
            "hypothesis": f"If we pair {random.choice(logics)} with aggressive {random.choice(shorts)}, we might capture the ETH volatility better.",
            "suggested_l": random.choice(logics),
            "suggested_s": random.choice(shorts),
            "timestamp": str(datetime.now())
        }
        return idea

import random # for brain logic

def main():
    brain = CreativeBrain()
    print("[Brain] Creative Crew is now ONLINE and THINKING in parallel.")
    
    while True:
        try:
            # 1. Generate a creative idea
            new_idea = brain.brainstorm()
            
            # 2. Append to a persistent ideas queue
            ideas = []
            if os.path.exists(IDEAS_FILE):
                with open(IDEAS_FILE, 'r') as f:
                    try: ideas = json.load(f)
                    except: pass
            
            ideas.append(new_idea)
            # Keep only last 5 ideas
            ideas = ideas[-5:]
            
            with open(IDEAS_FILE, "w") as f:
                json.dump(ideas, f, indent=2)
                
            print(f"[Brain] New strategy hypothesis queued: {new_idea['hypothesis']}")
            
            # Deep think sleep
            time.sleep(45) 
            
        except Exception as e:
            print(f"[Brain] Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
