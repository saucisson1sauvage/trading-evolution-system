"""
AI Context Generator for Genetic Strategy Evolution
Implements Prefix Caching and UID-Decoupling for efficient LLM payloads.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Try to import BLOCK_REGISTRY from gp_blocks
try:
    # Since gp_blocks.py is in user_data/strategies/, we need to adjust the path
    gp_blocks_path = project_root / "user_data" / "strategies" / "gp_blocks.py"
    # Use importlib to import it
    import importlib.util
    spec = importlib.util.spec_from_file_location("gp_blocks", gp_blocks_path)
    gp_blocks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gp_blocks)
    BLOCK_REGISTRY = gp_blocks.BLOCK_REGISTRY
except Exception as e:
    print(f"Note: Could not import BLOCK_REGISTRY: {e}")
    BLOCK_REGISTRY = {}


def build_static_anchor() -> str:
    """
    Construct a massive, unchanging prefix (>20,000 characters) that never changes.
    Contains the Arsenal, Personas, JSON Rules, and Elite Quant Encyclopedia.
    """
    # Build the Arsenal section
    arsenal_lines = ["# THE ARSENAL - ALL AVAILABLE BLOCKS\n"]
    
    if BLOCK_REGISTRY:
        for category, blocks in BLOCK_REGISTRY.items():
            arsenal_lines.append(f"\n## {category.upper()} BLOCKS:\n")
            for block_name, func in blocks.items():
                # Get description from function attribute, fallback to docstring
                description = getattr(func, 'description', None)
                if description is None:
                    description = func.__doc__ or "No description available."
                description = description.strip().split('\n')[0]
                arsenal_lines.append(f"- {block_name}: {description}")
    else:
        arsenal_lines.append("Failed to load blocks.")
    
    arsenal_text = "\n".join(arsenal_lines)
    
    # Build the Personas section
    personas_text = """
# THE PERSONAS

## a) The "Guided Outsider":
Focuses on Volatility and Trend breakouts. Uses traditional technical indicators but combines them in novel ways to capture momentum shifts. Prefers blocks like VOLATILE, TRENDING_UP/DOWN, CROSS_UP/DOWN with moving averages and Bollinger Bands.

## b) The "Alien Outsider":
Purely creative. Does not follow traditional logic. Acts like a beginner freely experimenting with Lego blocks. Combines indicators in chaotic, unexpected ways. May use VOLUME_SPIKE with constant comparisons, or mix unrelated indicators like RSI with BB_MIDDLE in unconventional ways.

## c) The "Fine-Tuner":
Looks at existing DNA and makes micro-adjustments to parameters or swaps a single block to improve performance. Focuses on small, precise changes to existing successful strategies.
"""
    
    # Build the JSON Rules section
    rules_text = """
# THE JSON RULES

RULE 1: No Hallucinations. Use EXACT block names from the Arsenal above. Do not invent new blocks.
RULE 2: Output EXACTLY a JSON array of 5 objects. DO NOT include lineage_ids or status keys.
RULE 3: Each object must have exactly these keys: 'type', 'entry_tree', and 'exit_tree'.
RULE 4: The 'type' must be one of: 'mutated_rank_1', 'mutated_rank_2', 'guided_outsider', 'alien_outsider_A', 'alien_outsider_B'.
RULE 5: Trees must be valid JSON objects with 'primitive', 'operator', 'left', 'right', 'children', 'parameters', or 'constant' keys as appropriate.
RULE 6: Keep parameter values within realistic ranges: windows between 5-50, std between 1.0-3.0, constants between 0-100.
"""
    
    # Build the massive Elite Quant Encyclopedia
    encyclopedia_text = """
# APPENDIX A: THE PHYSICS OF MARKET REGIMES (ELITE QUANT ENCYCLOPEDIA)

The cryptocurrency market is a highly non-stationary, heavily tailed, and structurally fragmented ecosystem. To design successful evolutionary logic using our AST (Abstract Syntax Tree) Genome, one must understand the underlying physics that dictate price action across different market regimes.

## 1. VOLATILITY CLUSTERING AND THE MANDELBROT HYPOTHESIS
Markets do not exhibit normal (Gaussian) distributions of returns. They exhibit "fat tails" where extreme events occur much more frequently than a standard bell curve predicts. Crucially, as observed by Benoit Mandelbrot, volatility clusters: large changes tend to be followed by large changes, of either sign, and small changes tend to be followed by small changes. In our AST logic, this means a "Volatility Breakout" strategy must include a gating mechanism. If the `VOLATILE` block triggers (e.g., ATR > SMA(ATR) * 1.5), the entry tree must execute quickly before the cluster dissipates. Conversely, mean-reverting strategies should actively avoid executing during volatility clusters, meaning the `NOT(VOLATILE)` wrapper is an essential survival tool for tight grid-trading logic.

## 2. TRADE TOXICITY AND VPIN (VOLUME-SYNCHRONIZED PROBABILITY OF INFORMED TRADING)
Not all volume is created equal. "Toxic" order flow occurs when informed traders (institutions, market makers) rapidly execute directional flow, running over uninformed liquidity providers. When a `VOLUME_SPIKE` occurs simultaneously with a strong `TRENDING_UP` or `CROSS_UP` signal, it often indicates toxicity. For trend followers, this is a highly profitable signal to piggyback on institutional flow. For market makers or mean-reverters, stepping in front of a `VOLUME_SPIKE` is financial suicide. Your logic must explicitly use volume as a confirming filter. A momentum oscillator crossing up (`CROSS_UP(RSI, 50)`) without a supporting `VOLUME_SPIKE` is likely a liquidity trap designed to hunt stops.

## 3. MEAN REVERSION IN NOISY ENVIRONMENTS
Mean reversion is the statistical tendency for an asset's price to return to its historical average. In crypto, mean reversion is highly effective during "Sideways" or "Consolidation" regimes but deadly during trending regimes. A master AST genome utilizes Bollinger Bands (`BB_UPPER`, `BB_LOWER`) combined with an oscillator (`RSI`) to detect exhaustion. A classic "Mean Reversion Flip" occurs when the price touches the `BB_LOWER` while the `RSI` is below 30, signaling an oversold state. However, to prevent catching a falling knife during a Crash regime, the logic must include a trend filter, ensuring that a slow `SMA` is relatively flat, or that the short-term `EMA` has begun curving upwards before the entry executes.

## 4. DISTINGUISHING HEALTHY TRENDS FROM LIQUIDITY TRAPS
A "Healthy Trend" is characterized by higher highs and higher lows with steady, manageable volume. A "Liquidity Trap" is characterized by an explosive, low-liquidity spike designed to trigger FOMO (Fear Of Missing Out), followed immediately by a harsh reversal. In AST terms, a healthy trend will trigger `TRENDING_UP(window=50)` consistently over many candles. A liquidity trap will trigger `CROSS_UP` on a fast moving average, but will fail a broader `GREATER_THAN(CLOSE, SMA(window=200))` check. Therefore, sophisticated entry trees must use multi-timeframe proxy logic: checking both a fast parameter (`window=14`) and a slow parameter (`window=100`) simultaneously using the `AND` operator to verify the structural integrity of the move.

## 5. THE PHYSICS OF ALGORITHMIC STOP LOSSES
Traditional stop losses (e.g., selling when price drops 5%) are fatal in cryptocurrency. They are visible to market makers who will purposefully drive the price down to "hunt" these clusters of liquidity before reversing the trend upward. 
In our AST framework, we do not use hard percentage stops. Instead, we use "Dynamic Logical Invalidation." An exit tree must define the exact mathematical state where the thesis of the trade is broken. If an entry was based on `CROSS_UP(EMA(10), SMA(50))`, the exit should not be a 5% drop, but rather `CROSS_DOWN(CLOSE, EMA(10))` combined with `VOLUME_SPIKE`. This proves the momentum has structurally died, rather than just suffering a momentary liquidity hunt. Defensive scalping strategies will use `VOLATILE` as an emergency ripcord, exiting the moment market chaos exceeds the strategy's operational parameters.

## 6. MARKOV CHAINS AND REGIME SHIFTS
The market is a Markov process where the next state depends heavily on the current state. A strategy designed for a high-volatility sideways market will bleed capital in a low-volatility trending market. Your generated genomes must attempt to identify the regime before executing. This is why `AND` operators are so vital. A genome should first ask "Are we in a trend?" using `TRENDING_UP`. Only if the answer is True should it ask "Is there an entry signal?" This dual-layer gating prevents the strategy from operating in the wrong mathematical universe.

# APPENDIX B: LEGO BLOCK SYNERGY MANUAL

Our Genetic Programming engine relies on atomic "Lego Blocks." Isolated blocks are mathematically weak; combined blocks create robust, non-linear edge.

## 1. THE MOMENTUM OSCILLATOR PARADOX (RSI)
The Relative Strength Index (RSI) is bounded between 0 and 100. Beginners use it as: IF RSI < 30 THEN BUY. In crypto, an asset can remain "oversold" (RSI < 30) while plunging 50% in value. The RSI is a *Momentum Oscillator*, not a price predictor. It must be gated. 
**The Synergy:** Wrap RSI checks inside Volatility or Trend filters. Example: `AND(LESS_THAN(RSI, 30), NOT(VOLATILE))`. This ensures you only buy the dip when the market is relatively calm, drastically reducing the chance of catching a falling knife.

## 2. THE MOVING AVERAGE WHIPSAW (EMA/SMA)
Moving averages (EMA, SMA) are lagging indicators. During sideways markets, `CROSS_UP(EMA, SMA)` will trigger repeatedly, resulting in death by a thousand cuts ("whipsaw"). 
**The Synergy:** Moving averages must be combined with Volume or Bollinger Band width. If an EMA crosses an SMA, it should only be trusted if the `BB_UPPER` and `BB_LOWER` are expanding (indicating a breakout from consolidation) or if confirmed by a `VOLUME_SPIKE`.

## 3. BOLLINGER BAND COMPRESSION (SQUEEZE)
Bollinger Bands (`BB_UPPER`, `BB_MIDDLE`, `BB_LOWER`) measure standard deviations from a mean. When the bands tighten, volatility is contracting. A breakout from this compression is highly explosive.
**The Synergy:** Comparing the width of the bands directly is difficult in our current AST, but we can proxy it. If `CLOSE` is very close to `BB_MIDDLE`, and suddenly `CROSS_UP(CLOSE, BB_UPPER)` occurs alongside a `VOLUME_SPIKE`, you have a high-probability breakout setup.

## 4. THE VOLUME/MOMENTUM DIVERGENCE
A classic signal of an impending reversal is when price momentum (RSI) is making higher highs, but volume is dropping. Since our AST does not natively compute divergence, we approximate it by requiring high volume for trend continuation entries, and rejecting entries where `VOLUME` is `LESS_THAN` its `SMA` even if the `RSI` is screaming buy. Always pair `VOLUME_SPIKE` with `CROSS_UP` to validate institutional participation.

# APPENDIX C: CRYPTO MICROSTRUCTURE & LATENCY

## 1. SLIPPAGE AND BID-ASK SPREAD IMPACT
In automated backtesting, we assume we can buy at the exact close price. In reality, executing a market order incurs slippage (the difference between expected price and executed price) and spread costs. High-frequency strategies that trigger hundreds of trades for 0.1% profit will be destroyed by trading fees and slippage.
**AST Implementation:** Exit logic must be loose enough to capture a meaningful macro move (e.g., 2%+). Do not build exit trees that close trades immediately upon minor pullbacks, as the spread will eat the profit. Use slower moving averages for exit trees (e.g., `CROSS_DOWN(CLOSE, SMA(50))`) to give the trade room to breathe.

## 2. LATENCY ARBITRAGE AND ORDER FLOW
Crypto exchanges suffer from latency. Relying on 1-minute `CROSS_UP` signals can result in entering trades after the algorithmic market makers have already front-run the move.
**AST Implementation:** Anticipatory logic is better than reactive logic. Instead of waiting for `CROSS_UP(EMA(10), EMA(20))`, a more sophisticated genome might measure the acceleration of the trend, perhaps triggering an entry when `CLOSE` is consistently held above `EMA(10)` while `VOLATILE` is false, anticipating the cross before the latency penalty hits.

# APPENDIX D: EVOLUTIONARY DYNAMICS & ALIEN MUTATIONS

The Genetic Engine explores a highly non-linear, multi-dimensional "Fitness Landscape." Imagine a mountain range covered in fog. The algorithm tries to climb to the highest peak.

## 1. THE LOCAL MAXIMUM TRAP
If we only use standard, logical combinations (like EMA crosses), the population quickly converges on a "Local Maximum"—a small hill that looks like the top but is actually far below the true peak. All strategies become incestuously similar, and evolution stagnates. 

## 2. THE ROLE OF THE "ALIEN OUTSIDER"
To escape a Local Maximum, the engine must make massive, illogical leaps into the unknown. This is why "Alien Outsider" mutations are critical. A genome that contains structurally bizarre logic—such as `AND(GREATER_THAN(VOLUME_SPIKE, 50), LESS_THAN(BB_UPPER, RSI))`—might initially seem absurd. However, this "Lego Noob" logic occasionally discovers hidden, non-Euclidean correlations in the market data that human intuition misses. 

## 3. STRUCTURAL VS POINT MUTATION
Point Mutation (changing a 14 to a 15) is hill-climbing; it refines an existing edge. Structural Mutation (swapping an entire `AND` block for a completely random `CROSS_DOWN` block) is a teleportation mechanism. The system requires both to survive the continuous drift of the cryptocurrency market.

## 4. SURVIVORSHIP BIAS IN AST DESIGN
When designing your genomes, you must avoid survivorship bias. A genome that simply buys the deepest dip and never sells will look like a genius in a permanent bull market, but will face a 90% drawdown during a "Crypto Winter." Your exit trees (`exit_tree`) are arguably more important than your entry trees. The most elite genomes use symmetrical logic: they enter on a volatility expansion and exit on a momentum collapse.

## 5. THE 'NOOB' ADVANTAGE IN HIGH-DIMENSIONAL SPACES
Human traders are burdened by cognitive bias. They want charts to make "sense." They believe RSI must be paired with MACD. The Genetic Algorithm does not care about human logic; it cares about topological geometry. A genome that executes `LESS_THAN(VOLUME_SPIKE, RSI)` makes zero grammatical sense to a human trader, but in the 100-dimensional space of the market order book, it might correlate perfectly with hidden whale accumulation. As the AI Architect, you must be willing to propose these "Lego Noob" combinations. Do not restrict yourself to textbook finance.

# APPENDIX E: 5 MASTER JSON EXAMPLES (STRICT SCHEMA VALIDATION)

The following examples demonstrate the pinnacle of AST genome construction. They are strictly valid, utilizing deep nesting, logical synergy, and exact primitive naming.

## EXAMPLE 1: THE "VOLATILITY BREAKOUT"
Captures explosive momentum shifts confirmed by heavy volume.
{
  "type": "guided_outsider",
  "entry_tree": {
    "operator": "AND",
    "children": [
      {
        "operator": "AND",
        "children": [
          {
            "primitive": "VOLATILE",
            "parameters": {"window": 20, "threshold": 2.5}
          },
          {
            "primitive": "VOLUME_SPIKE",
            "parameters": {"window": 14, "threshold": 3.0}
          }
        ]
      },
      {
        "primitive": "CROSS_UP",
        "left": {
          "primitive": "CLOSE"
        },
        "right": {
          "primitive": "BB_UPPER",
          "parameters": {"window": 20, "std": 2.0}
        }
      }
    ]
  },
  "exit_tree": {
    "operator": "OR",
    "children": [
      {
        "primitive": "CROSS_DOWN",
        "left": {
          "primitive": "CLOSE"
        },
        "right": {
          "primitive": "EMA",
          "parameters": {"window": 21}
        }
      },
      {
        "primitive": "LESS_THAN",
        "left": {
          "primitive": "RSI",
          "parameters": {"window": 14}
        },
        "right": {
          "constant": 40.0
        }
      }
    ]
  }
}

## EXAMPLE 2: THE "TREND-HARMONY"
A patient, trend-following engine that ignores chop and only enters when long and short trends align.
{
  "type": "mutated_rank_1",
  "entry_tree": {
    "operator": "AND",
    "children": [
      {
        "primitive": "TRENDING_UP",
        "parameters": {"window": 100}
      },
      {
        "operator": "AND",
        "children": [
          {
            "primitive": "CROSS_UP",
            "left": {
              "primitive": "EMA",
              "parameters": {"window": 13}
            },
            "right": {
              "primitive": "SMA",
              "parameters": {"window": 50}
            }
          },
          {
            "primitive": "GREATER_THAN",
            "left": {
              "primitive": "RSI",
              "parameters": {"window": 14}
            },
            "right": {
              "constant": 55.0
            }
          }
        ]
      }
    ]
  },
  "exit_tree": {
    "primitive": "TRENDING_DOWN",
    "parameters": {"window": 50}
  }
}

## EXAMPLE 3: THE "MEAN REVERSION FLIP"
Buys blood in the streets when the asset is severely oversold and touches the lower deviation bands.
{
  "type": "mutated_rank_2",
  "entry_tree": {
    "operator": "AND",
    "children": [
      {
        "primitive": "LESS_THAN",
        "left": {
          "primitive": "CLOSE"
        },
        "right": {
          "primitive": "BB_LOWER",
          "parameters": {"window": 20, "std": 2.5}
        }
      },
      {
        "operator": "AND",
        "children": [
          {
            "primitive": "LESS_THAN",
            "left": {
              "primitive": "RSI",
              "parameters": {"window": 14}
            },
            "right": {
              "constant": 25.0
            }
          },
          {
            "primitive": "NOT",
            "children": [
              {
                "primitive": "VOLATILE",
                "parameters": {"window": 10, "threshold": 2.0}
              }
            ]
          }
        ]
      }
    ]
  },
  "exit_tree": {
    "operator": "OR",
    "children": [
      {
        "primitive": "CROSS_UP",
        "left": {
          "primitive": "CLOSE"
        },
        "right": {
          "primitive": "BB_MIDDLE",
          "parameters": {"window": 20, "std": 2.5}
        }
      },
      {
        "primitive": "GREATER_THAN",
        "left": {
          "primitive": "RSI",
          "parameters": {"window": 14}
        },
        "right": {
          "constant": 70.0
        }
      }
    ]
  }
}

## EXAMPLE 4: THE "CHAOTIC ALIEN"
Illogical math that forces the GP engine to explore completely new mathematical quadrants.
{
  "type": "alien_outsider_A",
  "entry_tree": {
    "operator": "OR",
    "children": [
      {
        "operator": "AND",
        "children": [
          {
            "primitive": "LESS_THAN",
            "left": {
              "primitive": "SMA",
              "parameters": {"window": 11}
            },
            "right": {
              "primitive": "VOLUME"
            }
          },
          {
            "primitive": "NOT",
            "children": [
              {
                "primitive": "TRENDING_DOWN",
                "parameters": {"window": 33}
              }
            ]
          }
        ]
      },
      {
        "primitive": "CROSS_DOWN",
        "left": {
          "constant": 60.5
        },
        "right": {
          "primitive": "RSI",
          "parameters": {"window": 8}
        }
      }
    ]
  },
  "exit_tree": {
    "operator": "AND",
    "children": [
      {
        "primitive": "GREATER_THAN",
        "left": {
          "primitive": "BB_UPPER",
          "parameters": {"window": 15, "std": 1.5}
        },
        "right": {
          "primitive": "EMA",
          "parameters": {"window": 44}
        }
      },
      {
        "primitive": "VOLUME_SPIKE",
        "parameters": {"window": 7, "threshold": 1.2}
      }
    ]
  }
}

## EXAMPLE 5: THE "DEFENSIVE SCALPER"
Executes on minor momentum shifts but uses a hair-trigger exit tree to protect capital from whipsaws.
{
  "type": "alien_outsider_B",
  "entry_tree": {
    "operator": "AND",
    "children": [
      {
        "primitive": "CROSS_UP",
        "left": {
          "primitive": "EMA",
          "parameters": {"window": 5}
        },
        "right": {
          "primitive": "SMA",
          "parameters": {"window": 15}
        }
      },
      {
        "primitive": "GREATER_THAN",
        "left": {
          "primitive": "RSI",
          "parameters": {"window": 7}
        },
        "right": {
          "constant": 50.0
        }
      }
    ]
  },
  "exit_tree": {
    "operator": "OR",
    "children": [
      {
        "primitive": "CROSS_DOWN",
        "left": {
          "primitive": "CLOSE"
        },
        "right": {
          "primitive": "EMA",
          "parameters": {"window": 5}
        }
      },
      {
        "primitive": "LESS_THAN",
        "left": {
          "primitive": "RSI",
          "parameters": {"window": 7}
        },
        "right": {
          "constant": 45.0
        }
      },
      {
        "primitive": "VOLATILE",
        "parameters": {"window": 10, "threshold": 1.8}
      }
    ]
  }
}
"""
    
    # Combine all sections
    static_anchor = f"""{arsenal_text}

{personas_text}

{rules_text}

{encyclopedia_text}

# END OF STATIC ANCHOR - THIS SECTION NEVER CHANGES
# The following dynamic tail will contain current generation information.
"""
    
    return static_anchor


def build_dynamic_tail() -> str:
    """
    Construct the changing part of the payload.
    Loads hall_of_fame.json and state.json to format the scoreboard and mission.
    """
    # Load files
    strategies_path = Path(__file__).parent.parent / "user_data" / "strategies"
    hall_of_fame_path = strategies_path / "genomes" / "hall_of_fame.json"
    state_path = strategies_path / "state.json"
    
    try:
        with open(hall_of_fame_path, 'r') as f:
            hall_of_fame = json.load(f)
    except FileNotFoundError:
        hall_of_fame = []
    
    try:
        with open(state_path, 'r') as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {"current_generation": 0}
    
    # Format the Scoreboard - top 3 lineages
    scoreboard_lines = ["# SCOREBOARD - TOP LINEAGES\n"]
    
    for i, genome in enumerate(hall_of_fame[:3]):
        fitness = genome.get('fitness', 0)
        debuffed = genome.get('debuffed_fitness', fitness)
        lineage_id = genome.get('lineage_id', f'unknown_{i}')
        
        # Compact JSON for entry and exit trees
        entry_tree = genome.get('entry_tree', {})
        exit_tree = genome.get('exit_tree', {})
        
        # Create compact string representations - NO TRUNCATION
        entry_str = json.dumps(entry_tree, separators=(',', ':'))
        exit_str = json.dumps(exit_tree, separators=(',', ':'))
        
        scoreboard_lines.append(
            f"Rank {i+1} ({lineage_id}) | Fitness: {fitness:.3f} | "
            f"Debuffed: {debuffed:.3f} | "
            f"Entry: {entry_str} | "
            f"Exit: {exit_str}"
        )
    
    scoreboard_text = "\n".join(scoreboard_lines)
    
    # The Mission
    mission_text = f"""
# THE MISSION - GENERATION {state.get('current_generation', 0)}

Generate a JSON array with these exact 'type' tags in order:

1. 'mutated_rank_1' - Mutate the top-ranked lineage above (Rank 1). Make small adjustments to parameters or swap one block.
2. 'mutated_rank_2' - Mutate the second-ranked lineage (Rank 2). If no second lineage exists, use 'alien_outsider_fallback' instead.
3. 'guided_outsider' - Create a new strategy focusing on volatility and trend breakouts (Guided Outsider persona).
4. 'alien_outsider_A' - Create a purely creative, unconventional strategy (Alien Outsider persona).
5. 'alien_outsider_B' - Another alien outsider strategy, different from the previous one.

Remember: Output ONLY the JSON array with 5 objects, each with 'type', 'entry_tree', and 'exit_tree'.
"""
    
    dynamic_tail = f"""{scoreboard_text}

{mission_text}
"""
    
    return dynamic_tail


def main() -> None:
    """Main execution function."""
    print("Building AI Context with Prefix Caching...")
    
    # Build the two components
    static_anchor = build_static_anchor()
    dynamic_tail = build_dynamic_tail()
    
    # Load current generation
    state_path = Path(__file__).parent.parent / "user_data" / "strategies" / "state.json"
    try:
        with open(state_path, 'r') as f:
            state = json.load(f)
        current_generation = state.get('current_generation', 0)
    except FileNotFoundError:
        current_generation = 0
    
    # Combine into payload dictionary
    payload = {
        "static_anchor": static_anchor,
        "dynamic_tail": dynamic_tail,
        "current_generation": current_generation
    }
    
    # Write to cache file
    logs_path = Path(__file__).parent.parent / "user_data" / "logs"
    logs_path.mkdir(exist_ok=True)
    cache_path = logs_path / "ai_payload_cache.json"
    
    with open(cache_path, 'w') as f:
        json.dump(payload, f, indent=2)
    
    print(f"✓ Static anchor: {len(static_anchor)} characters")
    print(f"✓ Dynamic tail: {len(dynamic_tail)} characters")
    print(f"✓ Current generation: {current_generation}")
    print(f"✓ Payload written to: {cache_path}")
    
    if len(static_anchor) < 20000:
        print(f"⚠️ Warning: Static anchor is only {len(static_anchor)} characters (Target > 20,000)")
    else:
        print("✓ Static anchor exceeds 20,000 characters (Elite Quant Encyclopedia generated)")


if __name__ == "__main__":
    main()
