import os

def search_files(directory):
    keywords = ["70-90", "70–90", "3/16", "flared", "B-nut"]
    for root, dirs, files in os.walk(directory):
        # Exclude node_modules and .venv
        if "node_modules" in root or ".venv" in root or ".git" in root or ".mypy_cache" in root or ".pytest_cache" in root:
            continue
        for file in files:
            if file.endswith((".py", ".md", ".txt", ".json")):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            matches = [k for k in keywords if k.lower() in line.lower()]
                            if matches:
                                print(f"{os.path.relpath(path, directory)}:{line_num}: {line.strip()} (Matched: {matches})")
                except Exception as e:
                    pass

search_files("c:/Coding/mro-tts")
