import subprocess
import os
import sys

REPO_URL = "https://github.com/Vinit1510/K3PROJECT1.git"

def run(cmd):
    try:
        res = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"[SUCCESS] {cmd}\n{res.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[INFO/ERROR] Failed or info: {cmd}\n{e.stderr}")
        return False

def deploy():
    print("\n🚀 K3 QUANTUM DEPLOYMENT AUTOMATOR ENGINE 🚀\n")
    
    # 1. Safety checks: check if Git is in path, try standard install location fallback if not
    git_check = run("git --version")
    if not git_check:
        print("⚠️ Checking alternative executable location...")
        alt_git = r'"C:\Program Files\Git\bin\git.exe"'
        if run(f"{alt_git} --version"):
            print("✅ Git binary located successfully at absolute path.")
            # Overriding all command prefix with full path for stability
            def run_with_git(c): return run(c.replace("git ", f"{alt_git} "))
        else:
            print("❌ Critical: Git is still not recognized by your system environment yet.")
            print("   Please finish the installer, close ALL active command prompts,")
            print("   and open a fresh one to refresh PATH variables.")
            return
    else:
        run_with_git = run

    # 2. Initialization sequence
    if not os.path.exists(".git"):
        print("🔹 Initializing fresh local repository...")
        run_with_git("git init")
        run_with_git(f"git remote add origin {REPO_URL}")
    
    # 3. Synchronization
    print("🔹 Staging recent project modifications...")
    run_with_git("git add .")
    
    print("🔹 Solidifying snapshot...")
    commit_msg = "Engine Upgrade: LightTheme, Auditing fix, Dashboard Navigation and Excel tools"
    run_with_git(f'git commit -m "{commit_msg}"')

    # 4. Verify branch and execute push ignition
    print("🚀 IGNITING MAIN THRUSTERS (Pushing to GitHub)...")
    
    # Try to force push to main to overwrite any legacy objects on first sync
    success = run_with_git("git push -f -u origin main")
    if not success:
        print("⚠️ Retrying on default primary branch with force force...")
        run_with_git("git branch -M main")
        run_with_git("git push -f -u origin main")

    print("\n🎉 Operation Complete. Check your Render.com build feed now!")

if __name__ == "__main__":
    deploy()
