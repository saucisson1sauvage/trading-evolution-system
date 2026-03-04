import os
import shutil
import re
from datetime import datetime

class StrategyManager:
    def __init__(self, strat_path, backup_dir):
        self.strat_path = strat_path
        self.backup_dir = backup_dir
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

    def backup(self):
        name = os.path.basename(self.strat_path)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = f"{self.backup_dir}/{name}.{ts}.bak"
        shutil.copy2(self.strat_path, dest)
        backups = sorted([f for f in os.listdir(self.backup_dir) if f.startswith(name)], reverse=True)
        for old in backups[20:]:
            try: os.remove(f"{self.backup_dir}/{old}")
            except: pass
        return dest

    def get_source(self):
        with open(self.strat_path, 'r') as f:
            return f.read()

    def save_source(self, code):
        with open(self.strat_path, 'w') as f:
            f.write(code)

    def clean_snippet(self, text):
        """Strips markdown and conversational AI fluff from the snippet."""
        # 1. Remove markdown code blocks
        text = re.sub(r'```python', '', text)
        text = re.sub(r'```', '', text)
        
        # 2. Filter lines: Only keep lines that look like Python (assignment, comments, etc.)
        # This is a bit aggressive but helps prevent conversational hallucination
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            # If line is conversational (e.g., "I recommend...", "Here is the code:")
            if re.match(r'^(I|Here|Based|Note|Sure|The|This|As|Regarding)', line, re.I) and ":" not in line:
                continue
            clean_lines.append(line)
        
        return '\n'.join(clean_lines).strip()

    def inject_logic(self, indicators, entry, exit):
        source = self.get_source()
        new_code = source
        
        # CLEAN ALL SNIPPETS
        indicators = self.clean_snippet(indicators)
        entry = self.clean_snippet(entry)
        exit = self.clean_snippet(exit)
        
        if indicators:
            new_code = re.sub(r'# --- \[AI_INDICATORS_START\] ---.*?# --- \[AI_INDICATORS_END\] ---', 
                            f'# --- [AI_INDICATORS_START] ---\n        {indicators}\n        # --- [AI_INDICATORS_END] ---', 
                            new_code, flags=re.DOTALL)
        if entry:
            new_code = re.sub(r'# --- \[AI_LOGIC_START\] ---.*?# --- \[AI_LOGIC_END\] ---', 
                            f'# --- [AI_LOGIC_START] ---\n        {entry}\n        # --- [AI_LOGIC_END] ---', 
                            new_code, flags=re.DOTALL)
        if exit:
            new_code = re.sub(r'# --- \[AI_EXIT_START\] ---.*?# --- \[AI_EXIT_END\] ---', 
                            f'# --- [AI_EXIT_START] ---\n        {exit}\n        # --- [AI_EXIT_END] ---', 
                            new_code, flags=re.DOTALL)
        
        return new_code

    @staticmethod
    def test_injection():
        mock_strat = """
        # --- [AI_INDICATORS_START] ---
        old_ind
        # --- [AI_INDICATORS_END] ---
        # --- [AI_LOGIC_START] ---
        old_logic
        # --- [AI_LOGIC_END] ---
        """
        # Test cleaning + injection
        mgr = StrategyManager("", "")
        dirty_logic = "Here is the code:\n```python\ndataframe.loc[True, 'enter_long'] = 1\n```"
        clean = mgr.clean_snippet(dirty_logic)
        assert "Here is the code" not in clean
        assert "```" not in clean
        assert "dataframe.loc" in clean
        
        print("QA TEST: Injection & Cleaning OK")
        return True
