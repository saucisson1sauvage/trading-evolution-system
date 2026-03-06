import os
from pathlib import Path
import ast

def generate_map():
    project_root = Path(__file__).resolve().parent.parent
    map_file = project_root / "PROJECT_MAP.md"
    
    directories_to_scan = [
        project_root / "scripts",
        project_root / "user_data" / "strategies"
    ]
    
    markdown_content = ["# 🗺️ Crypto-Crew 4.0 Architecture Map\n\n*Auto-generated. Do not edit manually. Run `python scripts/generate_architecture_map.py` to update.*\n\n"]
    
    for directory in directories_to_scan:
        if not directory.exists():
            continue
            
        markdown_content.append(f"## 📁 {directory.relative_to(project_root)}\n")
        
        for root, _, files in os.walk(directory):
            for file in sorted(files):
                if file.endswith(".py") and file != "__init__.py":
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(project_root)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            tree = ast.parse(f.read())
                            docstring = ast.get_docstring(tree)
                            
                            markdown_content.append(f"### 📄 `{rel_path}`\n")
                            if docstring:
                                # Get just the first line/paragraph
                                summary = docstring.strip().split('\n\n')[0].replace('\n', ' ')
                                markdown_content.append(f"> {summary}\n\n")
                            else:
                                markdown_content.append("> *No module docstring provided.*\n\n")
                    except Exception as e:
                        markdown_content.append(f"### 📄 `{rel_path}`\n> *Error parsing file: {e}*\n\n")
                        
    with open(map_file, "w", encoding="utf-8") as f:
        f.writelines(markdown_content)
        
    print(f"Architecture map generated at: {map_file}")

if __name__ == "__main__":
    generate_map()
