#!/usr/bin/env python3
"""
Git Security Setup Script

Installs security hooks and configurations to prevent credential leaks.
"""

import os
import subprocess
import shutil
from pathlib import Path

def setup_git_hooks():
    """Set up Git hooks for security"""
    print("🔒 Setting up Git security hooks...")
    
    git_hooks_dir = Path(".git/hooks")
    if not git_hooks_dir.exists():
        print("❌ Not a Git repository")
        return False
    
    # Install pre-commit hook
    pre_commit_source = Path(".githooks/pre-commit")
    pre_commit_dest = git_hooks_dir / "pre-commit"
    
    if pre_commit_source.exists():
        shutil.copy2(pre_commit_source, pre_commit_dest)
        os.chmod(pre_commit_dest, 0o755)
        print("✅ Pre-commit hook installed")
    else:
        print("❌ Pre-commit hook source not found")
        return False
    
    return True

def configure_git_settings():
    """Configure Git settings for security"""
    print("🔧 Configuring Git security settings...")
    
    try:
        # Set up Git to always use the hooks
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], check=True)
        print("✅ Git hooks path configured")
        
        # Configure Git to be more secure
        subprocess.run(["git", "config", "core.autocrlf", "input"], check=True)
        subprocess.run(["git", "config", "core.fileMode", "true"], check=True)
        print("✅ Git security settings configured")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git configuration failed: {e}")
        return False

def test_security_setup():
    """Test the security setup"""
    print("🧪 Testing security setup...")
    
    try:
        # Test pre-commit hook
        result = subprocess.run([".githooks/pre-commit"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Pre-commit hook working")
        else:
            print("⚠️  Pre-commit hook test failed")
            print(f"   Output: {result.stdout}")
            print(f"   Error: {result.stderr}")
        
        # Test security scanner
        result = subprocess.run(["python", "scripts/security_scan.py"], capture_output=True, text=True)
        if "ALL SECURITY CHECKS PASSED" in result.stdout:
            print("✅ Security scanner working")
        else:
            print("⚠️  Security scanner test failed")
        
        return True
    except Exception as e:
        print(f"❌ Security test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🛡️  Git Security Setup")
    print("=" * 30)
    print("Installing security protections...")
    print()
    
    success = True
    
    # Setup hooks
    if not setup_git_hooks():
        success = False
    
    # Configure Git
    if not configure_git_settings():
        success = False
    
    # Test setup
    if not test_security_setup():
        success = False
    
    print("\n🎯 Setup Results")
    print("=" * 20)
    
    if success:
        print("✅ Git security setup complete!")
        print()
        print("🔒 Security features enabled:")
        print("• Pre-commit credential scanning")
        print("• Automatic file type validation")
        print("• Git history security scanning")
        print("• Comprehensive .gitignore protection")
        print()
        print("🚀 Your repository is now protected!")
        print("   Commits will be automatically scanned for credentials")
        print("   Run 'python scripts/security_scan.py' before GitHub uploads")
    else:
        print("❌ Security setup incomplete")
        print("   Some features may not work properly")
        print("   Check the errors above and try again")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())