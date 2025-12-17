import json
import random
import os
import math

# --- CONFIGURATION ---
INPUT_FILE = 'repo_summary.json'
OUTPUT_FILE = 'stratified_sample.json'
TOTAL_POPULATION = 16005  # Ton nombre N calculé précédemment
TARGET_SAMPLE_SIZE = 384  # n : 95% de confiance, marge d'erreur 5%

def generate_stratified_sample():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sampled_data = {}
    total_selected = 0
    
    print(f"--- Starting stratified sampling ---")
    print(f"Population (N): {TOTAL_POPULATION}")
    print(f"Target (n)    : {TARGET_SAMPLE_SIZE}")
    print("-" * 30)

    for repo_name, repo_data in data.items():
        # 1. Get the stratum population (number of files in the repo)
        files_list = repo_data.get('files', [])
        N_i = len(files_list)
        
        # Safety: if the list is empty but num_llm_files indicates otherwise
        if N_i == 0:
            continue

        # 2. Calculation: n_i = (N_i / N) * n
        # Use the ratio to determine the share
        ratio = N_i / TOTAL_POPULATION
        n_i_float = ratio * TARGET_SAMPLE_SIZE
        
        # 3. Smart rounding (to avoid 0 for small but significant repos)
        # Round to the nearest integer using round()
        n_i = int(round(n_i_float))
        
        # If calculation yields 0 but we absolutely want to represent this repo,
        # we can force 1 (optional, uncomment the line below if needed)
        # if n_i == 0 and N_i > 0: n_i = 1

        # Can't select more files than exist
        if n_i > N_i:
            n_i = N_i

        # 4. Random draw without replacement
        if n_i > 0:
            selected_files = random.sample(files_list, n_i)
            
            # Create an entry in the new dictionary
            sampled_data[repo_name] = repo_data.copy()
            sampled_data[repo_name]['files'] = selected_files
            sampled_data[repo_name]['num_llm_files'] = len(selected_files) # Update the count
            
            total_selected += len(selected_files)
            # print(f"  -> {repo_name}: {N_i} files -> {n_i} selected")

    # Sauvegarde
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        json.dump(sampled_data, out, indent=2, ensure_ascii=False)

    print("-" * 30)
    print(f"Sampling completed.")
    print(f"Generated file: {OUTPUT_FILE}")
    print(f"Total files selected: {total_selected} (Target: {TARGET_SAMPLE_SIZE})")
    print("Note: Actual total may vary slightly due to rounding.")

if __name__ == "__main__":
    generate_stratified_sample()