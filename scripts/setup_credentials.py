#!/usr/bin/env python3
"""
Credential Setup Script for Kite HFT Optimized Trading System

This script helps users securely set up their trading credentials
with industry-standard encryption.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.encryption import credential_manager


def main():
    """Main credential setup function"""
    print("🔐 Kite HFT Optimized - Secure Credential Setup")
    print("=" * 55)
    print()
    
    # Check if credentials already exist
    if credential_manager.is_configured():
        print("✅ Encrypted credentials already exist!")
        print()
        
        while True:
            choice = input("What would you like to do?\n"
                         "1. View credential status\n"
                         "2. Update specific credential\n"
                         "3. Reset all credentials\n"
                         "4. Exit\n"
                         "Enter choice (1-4): ").strip()
            
            if choice == "1":
                show_credential_status()
            elif choice == "2":
                update_credential()
            elif choice == "3":
                reset_credentials()
            elif choice == "4":
                print("👋 Goodbye!")
                return 0
            else:
                print("❌ Invalid choice. Please enter 1-4.")
                continue
            
            print()
    else:
        print("🆕 No encrypted credentials found. Let's set them up!")
        print()
        
        if setup_new_credentials():
            print("\n🎉 Setup complete! You can now run the trading system.")
            return 0
        else:
            print("\n❌ Setup failed. Please try again.")
            return 1


def show_credential_status():
    """Show which credentials are configured"""
    try:
        credentials = credential_manager.get_credentials()
        if credentials:
            print("\n📋 Configured credentials:")
            
            required_fields = ['api_key', 'api_secret', 'user_id', 'password', 'totp_secret']
            optional_fields = ['telegram_token', 'telegram_chat_id']
            
            for field in required_fields:
                status = "✅ Set" if credentials.get(field) else "❌ Missing"
                print(f"  {field}: {status}")
            
            print("\n📋 Optional credentials:")
            for field in optional_fields:
                status = "✅ Set" if credentials.get(field) else "➖ Not set"
                print(f"  {field}: {status}")
        else:
            print("❌ Could not decrypt credentials")
    except Exception as e:
        print(f"❌ Error checking credentials: {e}")


def update_credential():
    """Update a specific credential"""
    try:
        print("\n📝 Update Credential")
        print("-" * 20)
        
        fields = {
            '1': ('api_key', 'API Key'),
            '2': ('api_secret', 'API Secret'), 
            '3': ('user_id', 'User ID'),
            '4': ('password', 'Password'),
            '5': ('totp_secret', 'TOTP Secret'),
            '6': ('telegram_token', 'Telegram Bot Token'),
            '7': ('telegram_chat_id', 'Telegram Chat ID')
        }
        
        print("Which credential would you like to update?")
        for key, (field, display_name) in fields.items():
            print(f"{key}. {display_name}")
        
        choice = input("Enter choice (1-7): ").strip()
        
        if choice not in fields:
            print("❌ Invalid choice")
            return
        
        field_key, display_name = fields[choice]
        
        if field_key in ['api_secret', 'password', 'totp_secret', 'telegram_token']:
            import getpass
            new_value = getpass.getpass(f"Enter new {display_name}: ").strip()
        else:
            new_value = input(f"Enter new {display_name}: ").strip()
        
        if not new_value:
            print("❌ Value cannot be empty")
            return
        
        if credential_manager.update_credential(field_key, new_value):
            print(f"✅ {display_name} updated successfully")
        else:
            print(f"❌ Failed to update {display_name}")
            
    except KeyboardInterrupt:
        print("\n🛑 Update cancelled")
    except Exception as e:
        print(f"❌ Error updating credential: {e}")


def reset_credentials():
    """Reset all credentials"""
    try:
        print("\n⚠️  Reset All Credentials")
        print("-" * 25)
        print("This will permanently delete all encrypted credentials.")
        
        confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
        
        if confirm == 'yes':
            if credential_manager.reset_credentials():
                print("✅ All credentials reset successfully")
                
                setup_new = input("\nWould you like to set up new credentials now? (y/n): ").strip().lower()
                if setup_new == 'y':
                    setup_new_credentials()
            else:
                print("❌ Failed to reset credentials")
        else:
            print("🛑 Reset cancelled")
            
    except KeyboardInterrupt:
        print("\n🛑 Reset cancelled")
    except Exception as e:
        print(f"❌ Error resetting credentials: {e}")


def setup_new_credentials():
    """Set up new credentials"""
    try:
        print("📋 Security Information:")
        print("• Your credentials will be encrypted using AES-256")
        print("• You'll need a master password to encrypt/decrypt them")
        print("• The master password is NOT stored anywhere")
        print("• Choose a strong master password and remember it!")
        print()
        
        return credential_manager.setup_credentials(interactive=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Setup cancelled")
        return False
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)