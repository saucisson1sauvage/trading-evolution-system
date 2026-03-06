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
    Construct a massive, unchanging prefix (>4096 tokens) that never changes.
    Contains the Arsenal, Personas, JSON Rules, and a strict schema example.
    """
    # Build the Arsenal section
    arsenal_lines = ["# THE ARSENAL - ALL AVAILABLE BLOCKS\n"]
    
    # Use BLOCK_REGISTRY if available, otherwise use fallback
    if BLOCK_REGISTRY:
        for category, blocks in BLOCK_REGISTRY.items():
            arsenal_lines.append(f"\n## {category.upper()} BLOCKS:\n")
            for block_name, func in blocks.items():
                # Get function docstring or default description
                doc = func.__doc__ or "No description available."
                # Clean up docstring
                doc = doc.strip().split('\n')[0]
                arsenal_lines.append(f"- {block_name}: {doc}")
    else:
        # Fallback block descriptions
        block_categories = {
            'num': [
                ('OPEN', 'Returns the open price series.'),
                ('HIGH', 'Returns the high price series.'),
                ('LOW', 'Returns the low price series.'),
                ('CLOSE', 'Returns the close price series.'),
                ('VOLUME', 'Returns the trading volume series.'),
                ('RSI', 'Relative Strength Index. Parameters: window (default 14).'),
                ('EMA', 'Exponential Moving Average. Parameters: window.'),
                ('SMA', 'Simple Moving Average. Parameters: window.'),
                ('BB_UPPER', 'Bollinger Bands upper band. Parameters: window (default 20), std (default 2.0).'),
                ('BB_MIDDLE', 'Bollinger Bands middle band. Parameters: window (default 20), std (default 2.0).'),
                ('BB_LOWER', 'Bollinger Bands lower band. Parameters: window (default 20), std (default 2.0).'),
            ],
            'bool_helper': [
                ('TRENDING_UP', 'Detects if price is trending up over a window. Parameters: window (default 50).'),
                ('TRENDING_DOWN', 'Detects if price is trending down over a window. Parameters: window (default 50).'),
                ('VOLATILE', 'Identifies high volatility periods. Parameters: window (default 14), threshold (default 1.5).'),
                ('VOLUME_SPIKE', 'Detects unusual volume spikes. Parameters: window (default 20), threshold (default 2.0).'),
            ],
            'comparator': [
                ('GREATER_THAN', 'Returns True where s1 > s2. Accepts series or constant.'),
                ('LESS_THAN', 'Returns True where s1 < s2. Accepts series or constant.'),
                ('CROSS_UP', 'Returns True when s1 crosses above threshold.'),
                ('CROSS_DOWN', 'Returns True when s1 crosses below threshold.'),
            ],
            'operator': [
                ('AND', 'Logical AND between two boolean series.'),
                ('OR', 'Logical OR between two boolean series.'),
                ('NOT', 'Logical NOT of a boolean series.'),
            ]
        }
        
        for category, blocks in block_categories.items():
            arsenal_lines.append(f"\n## {category.upper()} BLOCKS:\n")
            for block_name, description in blocks:
                arsenal_lines.append(f"- {block_name}: {description}")
    
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
    
    # Build a massive JSON example to pad token count
    example_json = """
# STRICT SCHEMA EXAMPLE - VALID TREES:

Example entry_tree:
{
  "operator": "AND",
  "children": [
    {
      "primitive": "GREATER_THAN",
      "left": {
        "primitive": "RSI",
        "parameters": {"window": 14}
      },
      "right": {
        "constant": 30.0
      }
    },
    {
      "primitive": "CROSS_UP",
      "left": {
        "primitive": "EMA",
        "parameters": {"window": 20}
      },
      "right": {
        "primitive": "SMA",
        "parameters": {"window": 50}
      }
    }
  ]
}

Example exit_tree:
{
  "primitive": "CROSS_DOWN",
  "left": {
    "primitive": "CLOSE"
  },
  "right": {
    "primitive": "BB_UPPER",
    "parameters": {"window": 20, "std": 2.0}
  }
}

Another example entry_tree (simpler):
{
  "primitive": "VOLUME_SPIKE",
  "parameters": {"window": 15, "threshold": 2.0}
}

Example with nested operators:
{
  "operator": "OR",
  "children": [
    {
      "primitive": "TRENDING_UP",
      "parameters": {"window": 30}
    },
    {
      "operator": "AND",
      "children": [
        {
          "primitive": "LESS_THAN",
          "left": {
            "primitive": "BB_LOWER",
            "parameters": {"window": 20, "std": 2.0}
          },
          "right": {
            "constant": 25.5
          }
        },
        {
          "primitive": "VOLATILE",
          "parameters": {"window": 10, "threshold": 1.8}
        }
      ]
    }
  ]
}
"""
    
    # Build a massive appendix to ensure token count > 4096
    appendix_text = """
# APPENDIX: DETAILED RISK MANAGEMENT AND STRATEGY INSIGHTS

## 1. RISK MANAGEMENT FUNDAMENTALS
Risk management is the cornerstone of any successful trading strategy. It involves identifying, assessing, and prioritizing risks followed by coordinated application of resources to minimize, monitor, and control the probability or impact of unfortunate events. In algorithmic trading, risk management must be baked into the very fabric of the strategy's DNA. This includes position sizing, stop-loss mechanisms, maximum drawdown limits, and correlation analysis across multiple assets.

Effective risk management ensures that a single losing trade does not wipe out a significant portion of the trading capital. The Kelly Criterion, for instance, provides a mathematical framework for determining the optimal bet size given the edge and odds. However, in practice, traders often use a fraction of Kelly to reduce volatility. Another critical aspect is diversification across uncorrelated strategies, which can smooth equity curves and reduce the likelihood of catastrophic losses.

## 2. THE DANGERS OF OVERFITTING
Overfitting occurs when a strategy is excessively tailored to historical data, capturing noise rather than genuine market patterns. An overfitted strategy performs exceptionally well on in-sample data but fails miserably on unseen out-of-sample data or live trading. This is a pervasive problem in quantitative finance, especially when using complex machine learning models or genetic programming with many degrees of freedom.

To combat overfitting, practitioners employ several techniques: cross-validation, walk-forward analysis, Monte Carlo simulation, and out-of-sample testing. Additionally, parsimony—preferring simpler models with fewer parameters—often leads to more robust strategies. Regularization methods such as L1/L2 penalties can also help prevent overfitting by discouraging overly complex models.

## 3. ADDITIONAL JSON STRATEGY EXAMPLES

Example A – Complex Multi‑Indicator Entry with Nested Logic:
{
  "operator": "AND",
  "children": [
    {
      "primitive": "GREATER_THAN",
      "left": {
        "primitive": "RSI",
        "parameters": {"window": 21}
      },
      "right": {
        "constant": 40.0
      }
    },
    {
      "operator": "OR",
      "children": [
        {
          "primitive": "CROSS_UP",
          "left": {
            "primitive": "EMA",
            "parameters": {"window": 12}
          },
          "right": {
            "primitive": "SMA",
            "parameters": {"window": 26}
          }
        },
        {
          "primitive": "VOLATILE",
          "parameters": {"window": 10, "threshold": 1.7}
        }
      ]
    },
    {
      "primitive": "LESS_THAN",
      "left": {
        "primitive": "BB_UPPER",
        "parameters": {"window": 20, "std": 2.2}
      },
      "right": {
        "primitive": "CLOSE"
      }
    }
  ]
}

Example B – Pure Mean‑Reversion Exit:
{
  "primitive": "CROSS_DOWN",
  "left": {
    "primitive": "BB_MIDDLE",
    "parameters": {"window": 30, "std": 1.8}
  },
  "right": {
    "operator": "AND",
    "children": [
      {
        "primitive": "GREATER_THAN",
        "left": {
          "primitive": "CLOSE"
        },
        "right": {
          "primitive": "BB_UPPER",
          "parameters": {"window": 30, "std": 1.8}
        }
      },
      {
        "primitive": "VOLUME_SPIKE",
        "parameters": {"window": 15, "threshold": 2.5}
      }
    ]
  }
}

Example C – Trend‑Following with Volume Confirmation:
{
  "operator": "AND",
  "children": [
    {
      "primitive": "TRENDING_UP",
      "parameters": {"window": 60}
    },
    {
      "primitive": "GREATER_THAN",
      "left": {
        "primitive": "VOLUME"
      },
      "right": {
        "primitive": "SMA",
        "parameters": {"window": 30}
      }
    },
    {
      "operator": "NOT",
      "children": [
        {
          "primitive": "VOLATILE",
          "parameters": {"window": 14, "threshold": 2.0}
        }
      ]
    }
  ]
}

## 4. MARKET MICROSTRUCTURE CONSIDERATIONS
Liquidity, bid‑ask spreads, and market impact are crucial factors that can make or break a high‑frequency or medium‑frequency strategy. A strategy that appears profitable in backtests may become unprofitable when real‑world transaction costs are accounted for. Therefore, it is essential to model slippage and commission costs accurately during the development phase.

## 5. BEHAVIORAL FINANCE INSIGHTS
Human psychology often leads to predictable market anomalies such as herding, overreaction, and underreaction. Quant strategies that can identify and exploit these behavioral biases can achieve sustainable alpha. However, one must be cautious not to fall prey to the same biases during strategy development—confirmation bias and hindsight bias are particularly dangerous.

## 6. PORTFOLIO CONSTRUCTION AND OPTIMIZATION
Modern portfolio theory (MPT) and its extensions provide frameworks for constructing efficient portfolios that maximize return for a given level of risk. In a multi‑strategy context, correlation matrices, risk parity, and hierarchical risk parity can be used to allocate capital among various strategies dynamically.

## 7. REGULATORY AND COMPLIANCE CONSTRAINTS
Different jurisdictions impose varying restrictions on algorithmic trading, including circuit breakers, position limits, and reporting requirements. A robust strategy must be designed with these constraints in mind to avoid regulatory pitfalls.

## 8. TECHNOLOGY AND INFRASTRUCTURE
Low‑latency execution systems, robust data pipelines, and fault‑tolerant hardware are non‑negotiable for institutional‑grade algorithmic trading. Redundancy, failover mechanisms, and thorough disaster‑recovery plans ensure that the strategy can withstand unexpected technical failures.

## 9. CONTINUOUS IMPROVEMENT AND ADAPTATION
Financial markets are ever‑evolving; a strategy that works today may become obsolete tomorrow. Therefore, a systematic process for monitoring performance, detecting regime changes, and adapting the strategy accordingly is vital for long‑term success.

## 10. ETHICAL AND SOCIETAL IMPLICATIONS
Algorithmic trading can contribute to market stability or, conversely, exacerbate flash crashes. Practitioners have a responsibility to ensure their strategies do not harm market integrity and to engage in ethical design practices.
"""
    
    # Combine all sections
    static_anchor = f"""{arsenal_text}

{personas_text}

{rules_text}

{example_json}

{appendix_text}

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
    
    # Verify token count estimate (roughly 4 chars per token)
    total_chars = len(static_anchor) + len(dynamic_tail)
    estimated_tokens = total_chars / 4
    print(f"✓ Estimated total tokens: {estimated_tokens:.0f}")
    
    if len(static_anchor) / 4 < 4096:
        print("⚠️  Warning: Static anchor may be less than 4096 tokens")
    else:
        print("✓ Static anchor exceeds 4096 tokens (minimum requirement met)")


if __name__ == "__main__":
    main()
