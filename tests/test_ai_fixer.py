import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from scripts.ai_fixer import AIGenomeFixer

@patch('scripts.ai_fixer.requests.post')
def test_fix_genome_success(mock_post):
    # Mock the LLM response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '```json\n{"entry_tree": {"constant": 42.0}, "exit_tree": {"constant": 100.0}}\n```'
            }
        }]
    }
    mock_post.return_value = mock_response

    fixer = AIGenomeFixer()
    # Ensure it doesn't try to actually hit openrouter if key is missing by bypassing init logic
    fixer.active = True 
    fixer.api_url = "http://fake-url"

    dummy_genome = {"entry_tree": {"constant": 0.0}, "exit_tree": {"constant": 0.0}}
    fixed = fixer.fix_genome(dummy_genome)
    
    assert fixed is not None
    assert fixed["entry_tree"]["constant"] == 42.0
