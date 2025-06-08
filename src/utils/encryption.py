"""
Secure Credential Encryption and Management

High-security encryption system for storing sensitive trading credentials
using industry-standard encryption (Fernet/AES-256) with key derivation.
"""

import os
import base64
import hashlib
import getpass
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """
    Secure credential encryption and decryption using Fernet (AES-256)
    """
    
    def __init__(self, master_password: Optional[str] = None):
        """
        Initialize encryption with master password
        
        Args:
            master_password: Master password for encryption. If None, will prompt.
        """
        self.master_password = master_password
        self.salt_file = Path("config/.salt")
        self.credentials_file = Path("config/credentials.encrypted")
        
        # Create config directory if it doesn't exist
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate or load salt
        self.salt = self._get_or_create_salt()
        
        logger.debug("CredentialEncryption initialized")
    
    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create new one"""
        try:
            if self.salt_file.exists():
                with open(self.salt_file, 'rb') as f:
                    salt = f.read()
                logger.debug("Loaded existing salt")
                return salt
            else:
                # Generate new salt
                salt = os.urandom(16)
                with open(self.salt_file, 'wb') as f:
                    f.write(salt)
                logger.info("Generated new salt")
                return salt
        except Exception as e:
            logger.error(f"Error handling salt: {e}")
            raise
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=self.salt,
            iterations=100000,  # High iteration count for security
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _get_master_password(self) -> str:
        """Get master password from user or environment"""
        if self.master_password:
            return self.master_password
        
        # Check environment variable first
        env_password = os.getenv('KITE_MASTER_PASSWORD')
        if env_password:
            logger.debug("Using master password from environment")
            return env_password
        
        # Prompt user for password
        try:
            password = getpass.getpass("Enter master password for credential encryption: ")
            if not password:
                raise ValueError("Master password cannot be empty")
            return password
        except KeyboardInterrupt:
            logger.info("Password input cancelled")
            raise
        except Exception as e:
            logger.error(f"Error getting master password: {e}")
            raise
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Encrypt and save credentials to file
        
        Args:
            credentials: Dictionary containing sensitive credentials
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get master password
            password = self._get_master_password()
            
            # Derive encryption key
            key = self._derive_key(password)
            fernet = Fernet(key)
            
            # Convert credentials to JSON bytes
            credentials_json = json.dumps(credentials, indent=2)
            credentials_bytes = credentials_json.encode()
            
            # Encrypt credentials
            encrypted_data = fernet.encrypt(credentials_bytes)
            
            # Save to file
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set secure file permissions (readable only by owner)
            os.chmod(self.credentials_file, 0o600)
            
            logger.info(f"Credentials encrypted and saved to {self.credentials_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            return False
    
    def decrypt_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Decrypt and load credentials from file
        
        Returns:
            Dictionary containing decrypted credentials or None if failed
        """
        try:
            if not self.credentials_file.exists():
                logger.warning(f"Credentials file not found: {self.credentials_file}")
                return None
            
            # Get master password
            password = self._get_master_password()
            
            # Derive encryption key
            key = self._derive_key(password)
            fernet = Fernet(key)
            
            # Read encrypted data
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt credentials
            decrypted_bytes = fernet.decrypt(encrypted_data)
            credentials_json = decrypted_bytes.decode()
            
            # Parse JSON
            credentials = json.loads(credentials_json)
            
            logger.debug("Credentials decrypted successfully")
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            return None
    
    def update_credential(self, key: str, value: str) -> bool:
        """
        Update a single credential
        
        Args:
            key: Credential key (e.g., 'api_key')
            value: New credential value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing credentials
            credentials = self.decrypt_credentials() or {}
            
            # Update credential
            credentials[key] = value
            
            # Save updated credentials
            return self.encrypt_credentials(credentials)
            
        except Exception as e:
            logger.error(f"Failed to update credential {key}: {e}")
            return False
    
    def delete_credentials(self) -> bool:
        """Delete encrypted credentials file"""
        try:
            if self.credentials_file.exists():
                self.credentials_file.unlink()
                logger.info("Encrypted credentials file deleted")
            
            if self.salt_file.exists():
                self.salt_file.unlink()
                logger.info("Salt file deleted")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False


class SecureCredentialManager:
    """
    High-level credential management with multiple security layers
    """
    
    def __init__(self):
        """Initialize secure credential manager"""
        self.encryption = CredentialEncryption()
        self.credentials_cache = {}
        self.cache_loaded = False
        
        logger.debug("SecureCredentialManager initialized")
    
    def setup_credentials(self, interactive: bool = True) -> bool:
        """
        Interactive setup for first-time credential configuration
        
        Args:
            interactive: Whether to prompt user for input
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if interactive:
                print("\n🔐 Secure Credential Setup")
                print("=" * 40)
                print("Enter your Kite Connect API credentials.")
                print("These will be encrypted and stored securely.")
                print()
                
                credentials = {}
                
                # Collect credentials
                credentials['api_key'] = input("API Key: ").strip()
                credentials['api_secret'] = getpass.getpass("API Secret: ").strip()
                credentials['user_id'] = input("User ID: ").strip()
                credentials['password'] = getpass.getpass("Password: ").strip()
                credentials['totp_secret'] = getpass.getpass("TOTP Secret: ").strip()
                
                # Optional credentials
                print("\nOptional credentials (press Enter to skip):")
                telegram_token = input("Telegram Bot Token: ").strip()
                if telegram_token:
                    credentials['telegram_token'] = telegram_token
                
                telegram_chat_id = input("Telegram Chat ID: ").strip()
                if telegram_chat_id:
                    credentials['telegram_chat_id'] = telegram_chat_id
                
                # Validate required fields
                required_fields = ['api_key', 'api_secret', 'user_id', 'password', 'totp_secret']
                missing_fields = [field for field in required_fields if not credentials.get(field)]
                
                if missing_fields:
                    print(f"\n❌ Missing required fields: {missing_fields}")
                    return False
                
                # Encrypt and save
                success = self.encryption.encrypt_credentials(credentials)
                if success:
                    print("\n✅ Credentials encrypted and saved successfully!")
                    print("You can now run the trading system securely.")
                    return True
                else:
                    print("\n❌ Failed to encrypt credentials")
                    return False
            
            else:
                logger.info("Non-interactive credential setup requires environment variables")
                return self._setup_from_environment()
                
        except KeyboardInterrupt:
            print("\n\n🛑 Setup cancelled by user")
            return False
        except Exception as e:
            logger.error(f"Credential setup failed: {e}")
            return False
    
    def _setup_from_environment(self) -> bool:
        """Setup credentials from environment variables"""
        try:
            env_vars = {
                'api_key': 'KITE_API_KEY',
                'api_secret': 'KITE_API_SECRET',
                'user_id': 'KITE_USER_ID',
                'password': 'KITE_PASSWORD',
                'totp_secret': 'KITE_TOTP_SECRET',
                'telegram_token': 'KITE_TELEGRAM_TOKEN',
                'telegram_chat_id': 'KITE_TELEGRAM_CHAT_ID'
            }
            
            credentials = {}
            for key, env_var in env_vars.items():
                value = os.getenv(env_var)
                if value:
                    credentials[key] = value
            
            # Check required fields
            required_fields = ['api_key', 'api_secret', 'user_id', 'password', 'totp_secret']
            missing_fields = [field for field in required_fields if field not in credentials]
            
            if missing_fields:
                logger.error(f"Missing required environment variables for: {missing_fields}")
                return False
            
            return self.encryption.encrypt_credentials(credentials)
            
        except Exception as e:
            logger.error(f"Environment credential setup failed: {e}")
            return False
    
    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Get decrypted credentials
        
        Returns:
            Dictionary containing credentials or None if failed
        """
        try:
            if not self.cache_loaded:
                self.credentials_cache = self.encryption.decrypt_credentials() or {}
                self.cache_loaded = True
            
            return self.credentials_cache.copy()  # Return copy to prevent modification
            
        except Exception as e:
            logger.error(f"Failed to get credentials: {e}")
            return None
    
    def get_credential(self, key: str) -> Optional[str]:
        """
        Get a specific credential value
        
        Args:
            key: Credential key
            
        Returns:
            Credential value or None if not found
        """
        credentials = self.get_credentials()
        return credentials.get(key) if credentials else None
    
    def update_credential(self, key: str, value: str) -> bool:
        """
        Update a specific credential
        
        Args:
            key: Credential key
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        success = self.encryption.update_credential(key, value)
        if success:
            # Clear cache to force reload
            self.cache_loaded = False
            self.credentials_cache.clear()
        return success
    
    def is_configured(self) -> bool:
        """Check if credentials are configured"""
        return self.encryption.credentials_file.exists()
    
    def reset_credentials(self) -> bool:
        """Reset all credentials (delete encrypted file)"""
        success = self.encryption.delete_credentials()
        if success:
            self.cache_loaded = False
            self.credentials_cache.clear()
        return success


# Global credential manager instance
credential_manager = SecureCredentialManager()


def setup_credentials_cli():
    """Command-line interface for credential setup"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup encrypted credentials for Kite trading system")
    parser.add_argument("--reset", action="store_true", help="Reset existing credentials")
    parser.add_argument("--from-env", action="store_true", help="Setup from environment variables")
    
    args = parser.parse_args()
    
    try:
        if args.reset:
            print("🗑️  Resetting credentials...")
            if credential_manager.reset_credentials():
                print("✅ Credentials reset successfully")
            else:
                print("❌ Failed to reset credentials")
                return 1
        
        if not credential_manager.is_configured() or args.reset:
            success = credential_manager.setup_credentials(interactive=not args.from_env)
            return 0 if success else 1
        else:
            print("✅ Credentials already configured")
            print("Use --reset to reconfigure")
            return 0
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(setup_credentials_cli())