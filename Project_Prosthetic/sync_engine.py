"""
sync_engine.py — Exocortex Git Synchronization Layer
Standardizes how the Exocortex interacts with version control.

Usage:
    python sync_engine.py --status    # Check if safe to work
    python sync_engine.py --pull      # Safe update from remote
    python sync_engine.py --push "msg" # Commit and push work
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path("C:/Users/cerub/OneDrive/Dokumente/LLM")

def run_git(args, cwd=ROOT_DIR):
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[GIT ERROR] Command: git {' '.join(args)}")
        print(f"Error: {e.stderr.strip()}")
        return None

def check_status(verbose=False):
    """Check git status and return a summary dict."""
    status_out = run_git(["status", "--porcelain"])
    branch_out = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    remote_out = run_git(["rev-list", "--left-right", "--count", "origin/master...HEAD"])
    
    is_dirty = bool(status_out)
    ahead = 0
    behind = 0
    
    if remote_out:
        # distinct formatting like "0\t1" for behind\tahead
        parts = remote_out.split()
        if len(parts) >= 2:
            behind, ahead = map(int, parts[:2])
            
    if verbose:
        print(f"Branch: {branch_out}")
        print(f"Status: {'DIRTY' if is_dirty else 'CLEAN'}")
        print(f"Sync:   {ahead} ahead, {behind} behind")
        if is_dirty:
            print("\nUncommitted Changes:")
            print(status_out)
            
    return {
        "branch": branch_out,
        "dirty": is_dirty,
        "ahead": ahead,
        "behind": behind,
        "raw_status": status_out
    }

def safe_pull():
    """Safely pull from remote."""
    print("[SYNC] Checking status...")
    status = check_status()
    
    if status["dirty"]:
        print("[SYNC] Workspace is dirty. Stashing changes...")
        run_git(["stash", "save", "Exocortex Auto-Stash"])
    
    print("[SYNC] Pulling from origin...")
    res = run_git(["pull", "--rebase"])
    
    if res:
        print(f"[SYNC] {res}")
    else:
        print("[SYNC] Pull failed.")
        return False

    if status["dirty"]:
        print("[SYNC] Popping stash...")
        run_git(["stash", "pop"])
        
    print("[SYNC] Update complete.")
    return True

def smart_push(message):
    """Stage, commit, and push."""
    print("[SYNC] Preparing to push...")
    
    # Check if there's anything to commit
    status = check_status()
    if not status["dirty"] and status["ahead"] == 0:
        print("[SYNC] Nothing to commit or push.")
        return

    if status["dirty"]:
        run_git(["add", "."])
        run_git(["commit", "-m", message])
        print(f"[SYNC] Committed: {message}")
    
    print("[SYNC] Pushing to origin...")
    res = run_git(["push"])
    
    if res is not None:
        print("[SYNC] Push successful.")
    else:
        print("[SYNC] Push failed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exocortex Git Sync")
    parser.add_argument("--status", action="store_true", help="Check system status")
    parser.add_argument("--pull", action="store_true", help="Pull latest changes")
    parser.add_argument("--push", type=str, help="Commit and push with message")
    
    args = parser.parse_args()
    
    if args.status:
        check_status(verbose=True)
    elif args.pull:
        safe_pull()
    elif args.push:
        smart_push(args.push)
    else:
        check_status(verbose=True)
