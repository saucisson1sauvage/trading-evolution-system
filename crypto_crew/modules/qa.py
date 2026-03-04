import subprocess
import os

class QAManager:
    def __init__(self, runner, strategy_mgr):
        self.runner = runner
        self.strategy_mgr = strategy_mgr

    def check_strategy_syntax(self):
        """Verifies the strategy file is valid Python."""
        res = subprocess.run([self.runner.python, "-m", "py_compile", self.strategy_mgr.strat_path], 
                             capture_output=True, text=True)
        if res.returncode != 0:
            return False, res.stderr
        return True, "Syntax OK"

    def check_freqtrade_data(self):
        """Verifies we have data for backtesting."""
        cmd = [self.runner.python, self.runner.main, "list-data", "--userdir", self.runner.user_dir]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if "ETH/USDT" in res.stdout:
            return True, "Data OK"
        return False, "Data check failed or pair not found."

    def run_all_checks(self):
        results = {}
        results["Parser"] = self.runner.test_parsing()
        results["Injection"] = self.strategy_mgr.test_injection()
        
        ok, msg = self.check_strategy_syntax()
        results["Syntax"] = ok
        
        ok, msg = self.check_freqtrade_data()
        results["Data"] = ok
        
        return all(results.values()), results
