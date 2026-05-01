import os
import sys
import subprocess
import argparse

def clone_and_index(repo_url, target_path):
    project_name = repo_url.split("/")[-1].replace(".git", "")
    full_path = os.path.join(target_path, project_name)
    
    print(f"[*] Target Path: {full_path}")
    
    if os.path.exists(full_path):
        print(f"[!] Path already exists. Skipping clone.")
    else:
        print(f"[*] Cloning {repo_url}...")
        try:
            subprocess.run(["git", "clone", "--depth", "1", repo_url, full_path], check=True)
            print(f"[+] Successfully cloned to {full_path}")
        except subprocess.CalledProcessError as e:
            print(f"[-] Clone failed: {e}")
            return

    print(f"[*] Indexing key documentation in {full_path}...")
    doc_patterns = ["README.md", "docs/", "examples/", "CONTRIBUTING.md", "LICENSE"]
    found = []
    for pattern in doc_patterns:
        p = os.path.join(full_path, pattern)
        if os.path.exists(p):
            found.append(pattern)
    
    print(f"[+] Found documentation resources: {', '.join(found)}")
    print(f"[+] Research base ready at: {full_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clone and index GitHub documentation.")
    parser.add_argument("url", help="GitHub repository URL")
    parser.add_argument("--path", default="/storage/emulated/0/Documents", help="Base target path")
    args = parser.parse_args()
    
    clone_and_index(args.url, args.path)
