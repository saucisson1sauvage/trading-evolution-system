import subprocess
import shutil
import sys
from pathlib import Path

# Setup absolute paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CURRENT_GENOME_FILE = PROJECT_ROOT / "user_data" / "current_genome.json"
TEST_SCRIPT = PROJECT_ROOT / "tests" / "test_omniscience.py"

def is_tungsten_safe(genome_path: Path) -> bool:
    """
    Vets a candidate genome against the Omniscience test suite.
    1. Copies genome to current_genome.json
    2. Runs pytest on tests/test_omniscience.py
    3. Returns True if all tests pass, False otherwise.
    """
    if not genome_path.exists():
        print(f"Gatekeeper Error: {genome_path} does not exist.")
        return False

    # Ensure current_genome.json exists or create parent
    CURRENT_GENOME_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Backup existing current_genome.json if necessary? 
    # Usually it's a transient workspace file, so we just overwrite.
    shutil.copy(genome_path, CURRENT_GENOME_FILE)

    print(f"🛡️ Gatekeeper: Vetting {genome_path.name} against Omniscience Gauntlet...")
    
    # Run pytest
    # We use the local venv python if available
    python_bin = sys.executable
    
    try:
        # We only run the specific JSON integrity test to save time, 
        # but the prompt says "passes the 417+ tests", so we run the whole suite.
        result = subprocess.run(
            [python_bin, "-m", "pytest", str(TEST_SCRIPT), "-v"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
        
        if result.returncode == 0:
            return True
        else:
            print("Gatekeeper: Test Failure Output:")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"Gatekeeper: Execution Error: {e}")
        return False

if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if is_tungsten_safe(path):
            print("✅ VERIFIED TUNGSTEN SOLID")
        else:
            print("❌ REJECTED BY OMNISCIENCE")
