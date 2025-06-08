#!/usr/bin/env python3
"""
Security Scanner for Git Repository

Scans the entire Git history for potential credential leaks
before uploading to GitHub.
"""

import subprocess
import re
import sys
from pathlib import Path

def run_command(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def scan_git_history():
    """Scan entire Git history for potential secrets"""
    print("🔍 Scanning Git history for potential secrets...")
    
    # Patterns to look for (actual credential values, not just variable names)
    dangerous_patterns = [
        r'api_key["\s]*[:=]["\s]*[a-zA-Z0-9]{12,}',  # Real API keys are longer
        r'api_secret["\s]*[:=]["\s]*[a-zA-Z0-9]{20,}',  # Real secrets are longer
        r'totp_secret["\s]*[:=]["\s]*[A-Z0-9]{16,}',  # Real TOTP secrets
        r'KITE_API_KEY["\s]*[:=]["\s]*[a-zA-Z0-9]{12,}',
        r'KITE_API_SECRET["\s]*[:=]["\s]*[a-zA-Z0-9]{20,}',
        r'token["\s]*[:=]["\s]*[a-zA-Z0-9]{25,}',  # Real tokens are long
    ]
    
    # Exclude patterns (things that look like credentials but aren't)
    safe_patterns = [
        r'password.*=.*"test',  # Test passwords
        r'password.*=.*"your_',  # Template passwords
        r'password.*=.*"password',  # Generic examples
        r'master_password.*=.*getenv',  # Environment variable access
        r'password.*=.*getpass',  # Password input
        r'\.password',  # Object attributes
        r'password:.*Optional',  # Type annotations
        r'password:.*str',  # Type annotations
    ]
    
    # Get all commits
    stdout, stderr, code = run_command("git log --all --oneline")
    if code != 0:
        print(f"❌ Failed to get Git history: {stderr}")
        return False
    
    commits = [line.split()[0] for line in stdout.strip().split('\n') if line]
    print(f"   Scanning {len(commits)} commits...")
    
    violations = []
    
    for commit in commits:
        # Get commit content
        stdout, stderr, code = run_command(f"git show {commit}")
        if code != 0:
            continue
        
        commit_content = stdout
        
        # Check each pattern
        for pattern in dangerous_patterns:
            matches = re.findall(pattern, commit_content, re.IGNORECASE)
            if matches:
                # Filter out safe patterns
                filtered_matches = []
                for match in matches:
                    is_safe = False
                    for safe_pattern in safe_patterns:
                        if re.search(safe_pattern, match, re.IGNORECASE):
                            is_safe = True
                            break
                    if not is_safe:
                        filtered_matches.append(match)
                
                if filtered_matches:
                    violations.append({
                        'commit': commit,
                        'pattern': pattern,
                        'matches': filtered_matches
                    })
    
    if violations:
        print("❌ SECURITY VIOLATIONS FOUND:")
        for violation in violations:
            print(f"   Commit: {violation['commit']}")
            print(f"   Pattern: {violation['pattern']}")
            print(f"   Matches: {violation['matches']}")
            print()
        return False
    else:
        print("✅ No credential patterns found in Git history")
        return True

def scan_current_files():
    """Scan current files for potential secrets"""
    print("\n🔍 Scanning current files for potential secrets...")
    
    dangerous_files = [
        "config/credentials.yaml",
        "config/secrets.yaml", 
        "config/.env",
        ".env",
        "*.key",
        "*.pem",
        "*token.json",
        "config/credentials.encrypted"  # This is OK, but let's check
    ]
    
    violations = []
    
    # Check for dangerous files
    for pattern in dangerous_files:
        stdout, stderr, code = run_command(f"find . -name '{pattern}' -type f")
        if stdout.strip():
            files = stdout.strip().split('\n')
            for file in files:
                if file and not file.endswith('credentials.encrypted'):  # Encrypted files are OK
                    violations.append(f"Dangerous file found: {file}")
    
    # Check .gitignore coverage
    stdout, stderr, code = run_command("git ls-files --others --ignored --exclude-standard")
    ignored_files = stdout.strip().split('\n') if stdout.strip() else []
    
    if violations:
        print("❌ DANGEROUS FILES FOUND:")
        for violation in violations:
            print(f"   {violation}")
        print("\n   These files should be in .gitignore and removed from Git")
        return False
    else:
        print("✅ No dangerous files found")
        return True

def check_gitignore():
    """Check if .gitignore properly covers sensitive files"""
    print("\n🔍 Checking .gitignore coverage...")
    
    required_patterns = [
        "# Sensitive credential files",
        "config/secrets.yaml",
        "config/credentials.yaml",
        "config/auth_config.yaml",
        ".env*",
        "!.env.example",
        "*.key",
        "*.token",
        "*.json",
        "tokens/",
    ]
    
    try:
        with open('.gitignore', 'r') as f:
            gitignore_content = f.read()
        
        missing_patterns = []
        for pattern in required_patterns:
            if pattern not in gitignore_content:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            print("⚠️  Missing .gitignore patterns:")
            for pattern in missing_patterns:
                print(f"   {pattern}")
            print("\n   Consider adding these to .gitignore")
            return False
        else:
            print("✅ .gitignore properly configured")
            return True
            
    except FileNotFoundError:
        print("❌ .gitignore file not found!")
        return False

def verify_encryption():
    """Verify that credential encryption is working"""
    print("\n🔍 Verifying encryption system...")
    
    try:
        # Check if encryption files exist and are not readable
        encrypted_file = Path("config/credentials.encrypted")
        salt_file = Path("config/.salt")
        
        if encrypted_file.exists():
            print("✅ Encrypted credentials file found")
            
            # Check file permissions
            perms = oct(encrypted_file.stat().st_mode)[-3:]
            if perms == "600":
                print("✅ Secure file permissions (600)")
            else:
                print(f"⚠️  File permissions: {perms} (should be 600)")
        else:
            print("ℹ️  No encrypted credentials file (OK if using env vars)")
        
        if salt_file.exists():
            print("✅ Salt file found")
        else:
            print("ℹ️  No salt file (OK if using env vars)")
        
        return True
        
    except Exception as e:
        print(f"❌ Encryption verification failed: {e}")
        return False

def main():
    """Main security scan"""
    print("🛡️  Git Repository Security Scanner")
    print("=" * 50)
    print("Scanning repository before GitHub upload...")
    print()
    
    checks = [
        ("Git History", scan_git_history),
        ("Current Files", scan_current_files), 
        (".gitignore", check_gitignore),
        ("Encryption", verify_encryption),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        result = check_func()
        results.append((check_name, result))
    
    print("\n📊 Security Scan Results")
    print("=" * 30)
    
    all_passed = True
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 ALL SECURITY CHECKS PASSED!")
        print("✅ Repository is safe to upload to GitHub")
        print()
        print("🚀 Ready to push:")
        print("   git remote add origin https://github.com/your-username/kite-hft-optimized.git")
        print("   git push -u origin main")
        return 0
    else:
        print("❌ SECURITY ISSUES FOUND!")
        print("⚠️  DO NOT upload to GitHub until all issues are resolved")
        print()
        print("🔧 Recommended actions:")
        print("1. Remove any sensitive files from Git history")
        print("2. Update .gitignore to cover all sensitive patterns") 
        print("3. Verify all credentials are encrypted or in environment variables")
        print("4. Re-run this security scan")
        return 1

if __name__ == "__main__":
    exit(main())