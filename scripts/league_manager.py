import json
import sys
import argparse
from pathlib import Path
from scripts.paths import PathResolver

def get_league_path():
    return PathResolver.get_user_data_path() / "league.json"

def load_league():
    path = get_league_path()
    if not path.exists():
        return {"scores": []}
    with open(path, "r") as f:
        return json.load(f)

def save_league(data):
    with open(get_league_path(), "w") as f:
        json.dump(data, f, indent=2)

def run_gauntlet():
    print("Starting League Gauntlet...")
    # This would typically loop through all strategies or current DNA
    # For now, we call gauntlet.py logic
    from scripts.gauntlet import run_backtest
    score = run_backtest()
    
    if score is not None:
        league = load_league()
        league["scores"].append({"bot": "GeneticAssembler", "score": score})
        save_league(league)
        print(f"Gauntlet complete. Score {score} saved.")

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
            print(f"{i}. {entry['bot']}: {entry['score']}%")
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
