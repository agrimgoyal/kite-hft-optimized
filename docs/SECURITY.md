# Security Guide

## 🔒 Overview

The Kite HFT Optimized Trading System implements enterprise-grade security measures to protect your sensitive trading credentials and data. This guide covers all security aspects of the system.

## 🛡️ Credential Security

### Encryption Standards

- **Algorithm**: AES-256 encryption using Fernet (symmetric encryption)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations
- **Salt**: 16-byte random salt stored separately from encrypted data
- **Security Level**: Same encryption standards used by banks and financial institutions

### Storage Architecture

```
config/
├── .salt                    # Random salt (16 bytes)
├── credentials.encrypted    # Your encrypted credentials
└── config.yaml             # Public configuration (no secrets)
```

### Master Password Security

- **Never stored on disk** - you must remember it
- **High entropy recommended** - use a strong, unique password
- **Environment variable support** - `KITE_MASTER_PASSWORD` for automation
- **Prompt-based entry** - secure input without echo

## 🔧 Setup and Usage

### Initial Setup

```bash
# Interactive setup (recommended)
python scripts/setup_credentials.py

# Automated setup from environment variables
KITE_MASTER_PASSWORD="your_master_password" \
python scripts/setup_credentials.py --from-env
```

### Credential Management

```bash
# Check credential status
python scripts/setup_credentials.py

# Update specific credential
python scripts/setup_credentials.py
# Choose option 2 and follow prompts

# Reset all credentials (if compromised)
python scripts/setup_credentials.py --reset
```

### Environment Variables (Development)

For development environments, you can use environment variables:

```bash
# Copy template
cp .env.example .env

# Edit .env with your credentials
nano .env

# The system will use encrypted storage if available,
# otherwise fall back to environment variables
```

## 🔐 Security Best Practices

### 1. Master Password

- **Use a unique password** - don't reuse from other services
- **Make it strong** - minimum 12 characters with mixed case, numbers, symbols
- **Store securely** - use a password manager
- **Don't share** - never send via email, chat, or store in code

### 2. API Credentials

- **Enable 2FA** on your Kite Connect account
- **Use dedicated API keys** - don't reuse personal login credentials
- **Regular rotation** - change API credentials periodically
- **Monitor usage** - check API logs for unauthorized access

### 3. File Security

- **Secure permissions** - credential files have 600 permissions (owner read/write only)
- **No cloud sync** - exclude credential files from Dropbox, Google Drive, etc.
- **Regular backups** - backup your master password securely
- **Clean development** - never commit `.env` files or real credentials

### 4. Production Deployment

```bash
# Set master password via environment
export KITE_MASTER_PASSWORD="your_secure_master_password"

# Run application
python examples/basic_usage.py

# For Docker deployments
docker run -e KITE_MASTER_PASSWORD="password" your-image
```

## 🚨 Security Incident Response

### If Credentials Are Compromised

1. **Immediately reset** API credentials on Kite Connect portal
2. **Reset system credentials**:
   ```bash
   python scripts/setup_credentials.py --reset
   ```
3. **Change master password** during re-setup
4. **Review logs** for unauthorized access
5. **Monitor trading activity** for suspicious orders

### If Master Password Is Lost

1. **Reset credentials** (will delete encrypted data):
   ```bash
   python scripts/setup_credentials.py --reset
   ```
2. **Set up new credentials** with new master password
3. **Update any automation** that depends on the master password

## 📋 Security Checklist

### Before First Use

- [ ] Run `python scripts/setup_credentials.py`
- [ ] Choose a strong master password
- [ ] Verify `.env*` files are in `.gitignore`
- [ ] Enable 2FA on your Kite Connect account
- [ ] Test credential loading with a dry run

### Regular Security Maintenance

- [ ] Rotate API credentials every 3-6 months
- [ ] Update master password annually
- [ ] Review and clean old token files
- [ ] Monitor system logs for anomalies
- [ ] Keep dependencies updated

### Pre-Production Deployment

- [ ] Use encrypted credential storage (not environment variables)
- [ ] Set secure file permissions on deployment server
- [ ] Configure log rotation and monitoring
- [ ] Set up backup and disaster recovery
- [ ] Document incident response procedures

## 🔍 Security Auditing

### Verify Encryption

```python
# Test encryption strength
from src.utils.encryption import CredentialEncryption

encryption = CredentialEncryption()
test_data = {"test": "sensitive_data"}

# This should prompt for master password
encrypted = encryption.encrypt_credentials(test_data)
decrypted = encryption.decrypt_credentials()

print("Encryption test:", decrypted == test_data)
```

### Check File Permissions

```bash
# Verify secure permissions
ls -la config/credentials.encrypted
# Should show: -rw------- (600 permissions)

ls -la config/.salt
# Should show: -rw------- (600 permissions)
```

### Monitor Access

```bash
# Check recent access to credential files
stat config/credentials.encrypted
stat config/.salt

# Monitor system logs
tail -f logs/trading.log | grep -i credential
```

## ⚠️ Important Security Notes

### What Is Protected

- ✅ API keys and secrets
- ✅ User passwords and TOTP secrets
- ✅ Notification tokens (Telegram, etc.)
- ✅ All credential files are encrypted

### What Is NOT Protected

- ❌ Trading strategy logic (in source code)
- ❌ Configuration parameters (in config.yaml)
- ❌ Log files (may contain market data)
- ❌ Master password (stored in your memory only)

### Limitations

- **Single-device encryption** - credentials encrypted on one machine can't be easily moved
- **Master password dependency** - losing it means losing access to encrypted credentials
- **No password recovery** - the system cannot recover your master password
- **Local storage only** - credentials are not synced across machines

## 📞 Security Support

If you discover a security vulnerability:

1. **Do NOT** create a public GitHub issue
2. **Email** security@example.com with details
3. **Include** steps to reproduce the issue
4. **Allow** reasonable time for response and fixing

For security questions or concerns:
- 📧 Email: security@example.com
- 🔒 GPG Key: Available on request
- 📖 Documentation: This security guide

---

**Remember**: Security is a shared responsibility. The system provides the tools, but you must use them correctly and maintain good security hygiene.