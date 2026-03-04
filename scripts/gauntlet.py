import subprocess
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from scripts.paths import PathResolver
from scripts.league_manager import LeagueManager

logger = logging.getLogger(__name__)

class Gauntlet:
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.project_root = PathResolver.get_project_root()
        self.config_path = self.project_root / "config.json"
        self.data_dir = PathResolver.get_user_data_path() / "data" / "binance"
        
        # Check if config exists
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
    
    def run_monthly_backtests(self, year: int = 2025) -> List[Dict[str, Any]]:
        """Run backtests for each month of the specified year."""
        results = []
        
        for month in range(1, 13):
            # Format month with leading zero
            month_str = f"{month:02d}"
            # Define timerange for the month
            start_date = f"{year}-{month_str}-01"
            # Calculate end date (first day of next month)
            if month == 12:
                next_year = year + 1
                next_month = "01"
                end_date = f"{next_year}-{next_month}-01"
            else:
                next_month = f"{month + 1:02d}"
                end_date = f"{year}-{next_month}-01"
            
            timerange = f"{start_date}-{end_date}"
            
            # Create a temporary directory for export
            with tempfile.TemporaryDirectory() as tmpdir:
                export_path = Path(tmpdir) / "results.json"
                
                # Prepare command
                cmd = [
                    "python3", "-m", "freqtrade", "backtesting",
                    "--config", str(self.config_path),
                    "--strategy", self.strategy_name,
                    "--timerange", timerange,
                    "--timeframe", "1m",
                    "--export", "trades",
                    "--export-filename", str(export_path)
                ]
                
                logger.info(f"Running backtest for {start_date} to {end_date}")
                
                # Run subprocess
                env = {"PYTHONPATH": str(self.project_root)}
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    env=env,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Backtest failed for {timerange}: {result.stderr}")
                    # Add default metrics
                    metrics = {
                        "total_profit": 0.0,
                        "sharpe": 0.0,
                        "drawdown": 1.0,
                        "num_trades": 0
                    }
                else:
                    # Parse the exported results
                    metrics = self._parse_exported_results(export_path)
                
                metrics["month"] = month
                results.append(metrics)
        
        return results
    
    def _parse_exported_results(self, export_path: Path) -> Dict[str, Any]:
        """Parse exported JSON results to extract metrics."""
        metrics = {
            "total_profit": 0.0,
            "sharpe": 0.0,
            "drawdown": 1.0,
            "num_trades": 0
        }
        
        if not export_path.exists():
            logger.warning(f"Export file not found at {export_path}")
            return metrics
        
        try:
            with open(export_path, 'r') as f:
                data = json.load(f)
            
            # Extract metrics from the exported data
            # The structure may vary, but we'll look for common keys
            if isinstance(data, dict):
                # Look for strategy results
                for key, value in data.items():
                    if isinstance(value, dict):
                        # Check for metrics
                        if 'total_profit' in value:
                            metrics["total_profit"] = float(value.get('total_profit', 0))
                        if 'sharpe' in value:
                            metrics["sharpe"] = float(value.get('sharpe', 0))
                        if 'max_drawdown' in value:
                            metrics["drawdown"] = float(value.get('max_drawdown', 1.0))
                        if 'total_trades' in value:
                            metrics["num_trades"] = int(value.get('total_trades', 0))
                        
                        # Also check for profit_percent
                        if 'profit_percent' in value and metrics["total_profit"] == 0:
                            metrics["total_profit"] = float(value.get('profit_percent', 0))
                
                # If we didn't find metrics in nested dicts, check the top level
                if metrics["num_trades"] == 0:
                    if 'total_trades' in data:
                        metrics["num_trades"] = int(data.get('total_trades', 0))
                    if 'profit_total' in data:
                        metrics["total_profit"] = float(data.get('profit_total', 0))
                    if 'sharpe' in data:
                        metrics["sharpe"] = float(data.get('sharpe', 0))
                    if 'max_drawdown' in data:
                        metrics["drawdown"] = float(data.get('max_drawdown', 1.0))
            
            # Ensure drawdown is not zero
            if metrics["drawdown"] == 0:
                metrics["drawdown"] = 1.0
                
        except Exception as e:
            logger.error(f"Error parsing exported results: {e}")
        
        return metrics
    
    def calculate_overall_score(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall score from monthly results."""
        if not results:
            return {
                "total_profit": 0.0,
                "sharpe": 0.0,
                "drawdown": 1.0,
                "num_trades": 0,
                "score": 0.0
            }
        
        # Aggregate metrics
        # For profit, we can sum percentages (but be careful)
        total_profit = sum(r["total_profit"] for r in results)
        # For sharpe, average
        sharpe = sum(r["sharpe"] for r in results) / len(results)
        # For drawdown, take the maximum
        drawdown = max(r["drawdown"] for r in results)
        num_trades = sum(r["num_trades"] for r in results)
        
        # Calculate score
        if num_trades == 0:
            score = 0.0
        else:
            if drawdown == 0:
                drawdown = 1.0
            score = (total_profit * sharpe) / drawdown
        
        return {
            "total_profit": total_profit,
            "sharpe": sharpe,
            "drawdown": drawdown,
            "num_trades": num_trades,
            "score": score
        }

def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: python gauntlet.py <strategy_name>")
        sys.exit(1)
    
    strategy_name = sys.argv[1]
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    gauntlet = Gauntlet(strategy_name)
    results = gauntlet.run_monthly_backtests(2025)
    
    overall = gauntlet.calculate_overall_score(results)
    
    print(f"Overall metrics for {strategy_name}:")
    print(f"  Total Profit: {overall['total_profit']}%")
    print(f"  Sharpe Ratio: {overall['sharpe']}")
    print(f"  Max Drawdown: {overall['drawdown']}%")
    print(f"  Total Trades: {overall['num_trades']}")
    print(f"  Score: {overall['score']}")
    
    # Update league manager
    # For now, we'll update a placeholder slot
    # In a real implementation, we would need to decide which slot to update
    manager = LeagueManager()
    # Let's update outsider_1 for demonstration
    manager.update_slot(
        "outsider_1",
        strategy_name,
        overall["total_profit"],
        overall["sharpe"],
        overall["drawdown"],
        overall["num_trades"]
    )
    print(f"Updated league with {strategy_name} in outsider_1 slot")

if __name__ == "__main__":
    main()
