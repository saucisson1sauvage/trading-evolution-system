from pathlib import Path

class PathResolver:
    @staticmethod
    def get_project_root() -> Path:
        """Returns the absolute path to the project root directory."""
        return Path(__file__).parent.parent.resolve()

    @staticmethod
    def get_user_data_path() -> Path:
        return PathResolver.get_project_root() / "user_data"

    @staticmethod
    def get_strategies_path() -> Path:
        return PathResolver.get_user_data_path() / "strategies"

    @staticmethod
    def get_logs_path() -> Path:
        return PathResolver.get_user_data_path() / "logs"

    @staticmethod
    def get_scripts_path() -> Path:
        return PathResolver.get_project_root() / "scripts"

    @staticmethod
    def get_tests_path() -> Path:
        return PathResolver.get_project_root() / "tests"
