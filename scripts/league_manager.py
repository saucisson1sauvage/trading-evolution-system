import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import json
import argparse
from scripts.paths import PathResolver

def get_league_path():
    # Updated to user_data/strategies/league.json
    return PathResolver.get_strategies_path() / "league.json"

def load_league():
    path = get_league_path()
    if not path.exists():
        return {"scores": []}
    try:
        with open(path, "r") as f:
            data = json.load(f)
            if "scores" not in data:
                data["scores"] = []
            return data
    except Exception:
        return {"scores": []}

def save_league(data):
    if "scores" not in data:
        data["scores"] = []
    with open(get_league_path(), "w") as f:
        json.dump(data, f, indent=2)

def run_gauntlet():
    print("Starting League Gauntlet...")
    from scripts.gauntlet import run_backtest
    score = run_backtest()
    
    if score is not None:
        league = load_league()
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        league["scores"].append({
            "bot": "GeneticAssembler", 
            "score": score,
            "timestamp": timestamp
        })
        save_league(league)
        print(f"Gauntlet complete. Score {score}% saved to {get_league_path()}")

def rank():
    league = load_league()
    scores = league.get("scores", [])
    
    print("\n=== CURRENT LEADERBOARD ===")
    if not scores:
        print("No scores recorded yet.")
    else:
        # Sort by score descending
        sorted_scores = sorted(scores, key=lambda x: x['score'], reverse=True)
        for i, entry in enumerate(sorted_scores, 1):
            print(f"{i}. {entry['bot']}: {entry['score']}% (at {entry.get('timestamp', 'unknown')})")
    print("===========================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-gauntlet", action="store_true")
    parser.add_argument("--rank", action="store_true")
    args = parser.parse_args()

    if args.run_gauntlet:
        run_gauntlet()
    elif args.rank:
        rank()
    else:
        parser.print_help()
