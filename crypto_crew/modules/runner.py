import subprocess
import re
import os
import json
import logging

class FreqtradeRunner:
    def __init__(self, python_path, main_path, config_path, user_dir, cores=6):
        self.python = python_path
        self.main = main_path
        self.config = config_path
        self.user_dir = user_dir
        self.cores = cores
        self.cpu_list = ",".join(map(str, range(cores)))

    def run_backtest(self, strategy_name, timerange, strategy_path=None, param_file=None):
        cmd = ["taskset", "-c", self.cpu_list, self.python, self.main, "backtesting",
               "--strategy", strategy_name, "--config", self.config,
               "--timerange", timerange, "--userdir", self.user_dir, "--timeframe", "5m"]
        
        if strategy_path:
            cmd += ["--strategy-path", strategy_path]
        if param_file and os.path.exists(param_file):
            cmd += ["--strategy-parameters", param_file]

        res = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
        return res

    def run_hyperopt(self, strategy_name, timerange, epochs=50, jobs=2):
        cmd = ["taskset", "-c", self.cpu_list, self.python, self.main, "hyperopt",
               "--strategy", strategy_name, "--config", self.config,
               "--timerange", timerange, "--userdir", self.user_dir,
               "--epochs", str(epochs), "--hyperopt-loss", "OnlyProfitHyperOptLoss",
               "-j", str(jobs), "--spaces", "buy", "sell", "--timeframe", "5m"]
        
        res = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
        return res

    def parse_metrics(self, output):
        clean = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', output)
        metrics = {
            "profit_pct": 0.0, 
            "trades": 0, 
            "win_rate": 0.0, 
            "drawdown": 0.0,
            "profit_factor": 0.0,
            "sharpe": 0.0,
            "exit_reasons": {}
        }
        
        # 1. BASE ROW PARSING
        row_match = re.search(r'│\s+[\w]+\s+│\s+(\d+)\s+│\s*([\d\.-]+)\s*│\s*([\d\.-]+)\s*│\s*([\d\.-]+)\s*│', clean)
        if row_match:
            metrics["trades"] = int(row_match.group(1))
            metrics["profit_pct"] = float(row_match.group(4))
            
            win_match = re.search(r'(\d+\.\d+)\s+│\s+[\d\.]+ USDT', clean)
            if win_match: metrics["win_rate"] = float(win_match.group(1))
            
            dd_match = re.search(r'Absolute\s*drawdown\s*│\s*[\d\.]+\s*USDT\s*\(([\d\.]+)%\)', clean)
            if dd_match: metrics["drawdown"] = float(dd_match.group(1))

        # 2. RICH METRICS (Sharpe, Profit Factor)
        pf_match = re.search(r'Profit factor\s*│\s*([\d\.]+)', clean)
        if pf_match: metrics["profit_factor"] = float(pf_match.group(1))
        
        sh_match = re.search(r'Sharpe\s*Ratio\s*│\s*([\d\.-]+)', clean)
        if sh_match: metrics["sharpe"] = float(sh_match.group(1))

        # 3. EXIT REASONS (Crucial for AI to understand behavior)
        # Parses the EXIT REASON STATS table
        exit_matches = re.findall(r'│\s+([\w_]+)\s+│\s+(\d+)\s+│', clean)
        for reason, count in exit_matches:
            if reason not in ["TOTAL", "Exit", "Reason"]: # Filter table headers
                metrics["exit_reasons"][reason] = int(count)
                
        return metrics

    @staticmethod
    def test_parsing():
        sample = """
        │ EvolutionaryVolScaler │     46 │         0.71 │          32.538 │         3.25 │     14:45:00 │   21    24     1  45.7 │ 9.164 USDT  0.88% │
        Absolute drawdown │ 9.164 USDT (0.88%)
        Profit factor │ 4.55
        Sharpe Ratio │ 10.97
        EXIT REASON STATS
        │ Exit Reason │ Exits │
        │         roi │    40 │
        │    stoploss │     6 │
        """
        runner = FreqtradeRunner("", "", "", "")
        m = runner.parse_metrics(sample)
        assert m["trades"] == 46
        assert m["profit_pct"] == 3.25
        assert m["profit_factor"] == 4.55
        assert m["exit_reasons"].get("roi") == 40
        assert m["exit_reasons"].get("stoploss") == 6
        print("QA TEST: Rich Parser OK")
        return True
