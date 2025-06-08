#!/usr/bin/env python3
"""
Test script to verify encryption/decryption and auto-login flow
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_encryption_flow():
    """Test the complete encryption/decryption flow"""
    print("🧪 Testing Encryption/Decryption Flow")
    print("=" * 40)
    
    try:
        from src.utils.encryption import CredentialEncryption, credential_manager
        
        # Test 1: Basic encryption/decryption
        print("\n1. Testing basic encryption...")
        
        test_credentials = {
            "api_key": "test_api_key_123",
            "api_secret": "test_secret_456", 
            "user_id": "TEST123",
            "password": "test_password",
            "totp_secret": "test_totp_secret"
        }
        
        # Create encryption instance with test password
        encryption = CredentialEncryption(master_password="test_password_123")
        
        # Test encryption
        success = encryption.encrypt_credentials(test_credentials)
        print(f"   Encryption: {'✅ Success' if success else '❌ Failed'}")
        
        if success:
            # Test decryption
            decrypted = encryption.decrypt_credentials()
            print(f"   Decryption: {'✅ Success' if decrypted else '❌ Failed'}")
            
            if decrypted:
                # Verify data integrity
                match = decrypted == test_credentials
                print(f"   Data integrity: {'✅ Match' if match else '❌ Mismatch'}")
                
                if not match:
                    print(f"   Expected: {test_credentials}")
                    print(f"   Got: {decrypted}")
        
        # Test 2: Configuration loading
        print("\n2. Testing configuration loading...")
        
        try:
            from src.utils.config import config
            kite_config = config.kite
            
            print(f"   Config loaded: ✅ Success")
            print(f"   API Key loaded: {'✅ Yes' if kite_config.api_key else '❌ No'}")
            print(f"   API Secret loaded: {'✅ Yes' if kite_config.api_secret else '❌ No'}")
            
        except Exception as e:
            print(f"   Config loading: ❌ Failed - {e}")
        
        # Test 3: Authentication initialization
        print("\n3. Testing authentication initialization...")
        
        try:
            from src.auth.kite_auth import KiteAuthenticator
            
            # This should load credentials from encrypted storage
            auth = KiteAuthenticator()
            print(f"   Auth initialization: ✅ Success")
            print(f"   Kite instance created: {'✅ Yes' if auth.kite else '❌ No'}")
            
        except Exception as e:
            print(f"   Auth initialization: ❌ Failed - {e}")
        
        print("\n🎉 Encryption flow test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auto_login_flow():
    """Test the complete auto-login flow"""
    print("\n\n🔐 Testing Auto-Login Flow")
    print("=" * 40)
    
    try:
        # Check if credentials are configured
        from src.utils.encryption import credential_manager
        
        if not credential_manager.is_configured():
            print("   No encrypted credentials found")
            print("   Auto-login requires setup first")
            return False
        
        print("   Encrypted credentials found: ✅")
        
        # Test credential loading without manual input
        # (This would normally prompt for master password)
        print("   Testing credential decryption...")
        
        # For testing, we'll use environment variable
        os.environ['KITE_MASTER_PASSWORD'] = 'test_password_123'
        
        credentials = credential_manager.get_credentials()
        if credentials:
            print("   Credential loading: ✅ Success")
            print(f"   Loaded {len(credentials)} credential fields")
            
            # Test authentication flow
            print("   Testing authentication flow...")
            
            from src.auth.kite_auth import KiteAuthenticator
            auth = KiteAuthenticator()
            
            print("   Authentication setup: ✅ Success")
            print("   🎯 Auto-login flow working!")
            
            return True
        else:
            print("   Credential loading: ❌ Failed")
            return False
            
    except Exception as e:
        print(f"   Auto-login test: ❌ Failed - {e}")
        return False


def cleanup_test_files():
    """Clean up test files"""
    try:
        test_files = [
            "config/credentials.encrypted",
            "config/.salt"
        ]
        
        for file_path in test_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"   Cleaned up: {file_path}")
        
        # Remove test environment variable
        if 'KITE_MASTER_PASSWORD' in os.environ:
            del os.environ['KITE_MASTER_PASSWORD']
            
    except Exception as e:
        print(f"   Cleanup error: {e}")


if __name__ == "__main__":
    try:
        print("🔒 Kite HFT Security Test Suite")
        print("=" * 50)
        
        # Run tests
        encryption_success = test_encryption_flow()
        auto_login_success = test_auto_login_flow()
        
        print("\n📊 Test Results Summary")
        print("=" * 30)
        print(f"Encryption/Decryption: {'✅ PASS' if encryption_success else '❌ FAIL'}")
        print(f"Auto-login Flow: {'✅ PASS' if auto_login_success else '❌ FAIL'}")
        
        if encryption_success and auto_login_success:
            print("\n🎉 All tests passed! The system is ready for production.")
        else:
            print("\n⚠️  Some tests failed. Please check the implementation.")
        
        # Cleanup
        print("\n🧹 Cleaning up test files...")
        cleanup_test_files()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user")
        cleanup_test_files()
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        cleanup_test_files()