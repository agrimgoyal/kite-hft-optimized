#!/usr/bin/env python3
"""
Test Auto-Login Flow

This script demonstrates and tests the automatic login capability
using encrypted credentials.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_auto_login():
    """Test the complete auto-login flow"""
    print("🔐 Testing Auto-Login Flow")
    print("=" * 40)
    
    try:
        from utils.encryption import credential_manager
        from utils.config import config
        
        # Step 1: Check if credentials are configured
        print("1. Checking credential configuration...")
        
        if not credential_manager.is_configured():
            print("❌ No encrypted credentials found")
            print("   Please run: python scripts/setup_credentials.py")
            return False
        
        print("✅ Encrypted credentials found")
        
        # Step 2: Test credential loading
        print("\n2. Testing credential decryption...")
        
        # For auto-login, master password should be in environment
        master_password = os.getenv('KITE_MASTER_PASSWORD')
        
        if not master_password:
            print("⚠️  KITE_MASTER_PASSWORD not set in environment")
            print("   For true auto-login, set this environment variable")
            print("   For now, you'll be prompted for the master password")
        
        credentials = credential_manager.get_credentials()
        
        if not credentials:
            print("❌ Failed to decrypt credentials")
            print("   Check your master password")
            return False
        
        print("✅ Credentials decrypted successfully")
        print(f"   Loaded {len(credentials)} credential fields")
        
        # Step 3: Test configuration loading
        print("\n3. Testing configuration loading...")
        
        kite_config = config.kite
        
        if not kite_config.api_key:
            print("❌ API key not loaded in configuration")
            return False
        
        print(f"✅ API key loaded: {kite_config.api_key[:8]}...")
        print(f"✅ User ID loaded: {kite_config.user_id}")
        
        # Step 4: Test authentication initialization
        print("\n4. Testing authentication initialization...")
        
        from auth.kite_auth import KiteAuthenticator
        
        auth = KiteAuthenticator()
        print("✅ KiteAuthenticator created successfully")
        
        if auth.kite:
            print("✅ KiteConnect instance initialized")
        else:
            print("❌ KiteConnect instance not created")
            return False
        
        # Step 5: Summary
        print("\n🎉 Auto-Login Test Results")
        print("=" * 30)
        print("✅ Credential storage working")
        print("✅ Credential decryption working")
        print("✅ Configuration loading working")
        print("✅ Authentication initialization working")
        
        if master_password:
            print("✅ Full auto-login capability (no prompts)")
        else:
            print("⚠️  Partial auto-login (password prompt required)")
            print("   Set KITE_MASTER_PASSWORD for full automation")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Auto-login test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_auto_login_setup():
    """Show how to set up true auto-login"""
    print("\n\n📋 How to Enable True Auto-Login")
    print("=" * 40)
    print()
    print("1. Set master password in environment:")
    print("   export KITE_MASTER_PASSWORD='your_master_password'")
    print()
    print("2. For permanent setup, add to your shell profile:")
    print("   echo 'export KITE_MASTER_PASSWORD=\"your_password\"' >> ~/.bashrc")
    print("   source ~/.bashrc")
    print()
    print("3. For Docker/production deployment:")
    print("   docker run -e KITE_MASTER_PASSWORD='password' your-image")
    print()
    print("4. For systemd services, add to service file:")
    print("   Environment=KITE_MASTER_PASSWORD=your_password")
    print()
    print("🔒 Security Notes:")
    print("• Use a strong, unique master password")
    print("• Keep environment variables secure")
    print("• Consider using secret management systems in production")
    print("• Never put passwords in scripts or config files committed to Git")

def main():
    """Main function"""
    try:
        success = test_auto_login()
        
        if success:
            print("\n🎯 Auto-login is working!")
            
            # Check if we have full automation
            if os.getenv('KITE_MASTER_PASSWORD'):
                print("🚀 You have FULL auto-login capability!")
                print("   The system can start without any user input.")
            else:
                print("🔧 You have PARTIAL auto-login capability.")
                print("   Set KITE_MASTER_PASSWORD for full automation.")
                show_auto_login_setup()
        else:
            print("\n❌ Auto-login setup needs attention.")
            print("   Please run: python scripts/setup_credentials.py")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n🛑 Test cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())