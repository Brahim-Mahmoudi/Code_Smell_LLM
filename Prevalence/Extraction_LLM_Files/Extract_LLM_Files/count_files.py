import json
import os

def count_total_files(json_file_path):
    # Check that the file exists
    if not os.path.exists(json_file_path):
        print(f"Error: The file '{json_file_path}' was not found.")
        return

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total_files = 0
        total_repos = 0

        print(f"--- Analyzing {json_file_path} ---")

        # The JSON appears to be a dictionary where each key is a repo name
        for repo_name, repo_data in data.items():
            # Retrieve the number of files.
            # Use .get() to avoid an error if the key is missing.
            count = repo_data.get('num_llm_files', 0)
            
            # Alternative: If you want to count the actual length of the 'files' list:
            # count = len(repo_data.get('files', []))
            
            total_files += count
            total_repos += 1
            
            # Optional: print details per repo
            # print(f"- {repo_name}: {count} files")

        print("-" * 30)
        print(f"Success")
        print(f"Number of repositories analyzed: {total_repos}")
        print(f"TOTAL number of files          : {total_files}")

    except json.JSONDecodeError:
        print("Error: File is not valid JSON.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Exécution du script
if __name__ == "__main__":
    # Ensure the filename matches yours
    target_file = 'repo_summary.json'
    count_total_files(target_file)