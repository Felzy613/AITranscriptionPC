"""
Encryption utilities for storing sensitive data (API keys) locally
Uses Fernet (symmetric encryption) from cryptography library
"""

import os
import json
from cryptography.fernet import Fernet
from pathlib import Path


class SecureStorage:
    """Encrypts and stores sensitive data locally"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".aitpc"
        self.config_dir.mkdir(exist_ok=True)
        
        self.key_file = self.config_dir / ".key"
        self.data_file = self.config_dir / "config.enc"
        
        self._ensure_encryption_key()
    
    def _ensure_encryption_key(self):
        """Create encryption key if it doesn't exist"""
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            # Protect key file on Windows
            if os.name == 'nt':
                os.system(f'attrib +h "{self.key_file}"')  # Hide file
    
    def _get_cipher(self):
        """Get Fernet cipher using stored key"""
        key = self.key_file.read_bytes()
        return Fernet(key)
    
    def save(self, data: dict):
        """Encrypt and save data"""
        cipher = self._get_cipher()
        json_data = json.dumps(data).encode()
        encrypted = cipher.encrypt(json_data)
        self.data_file.write_bytes(encrypted)
    
    def load(self) -> dict:
        """Decrypt and load data"""
        if not self.data_file.exists():
            return {}
        
        try:
            cipher = self._get_cipher()
            encrypted = self.data_file.read_bytes()
            json_data = cipher.decrypt(encrypted)
            return json.loads(json_data.decode())
        except Exception as e:
            print(f"Error decrypting config: {e}")
            return {}
    
    def has_api_key(self) -> bool:
        """Check if API key is stored"""
        data = self.load()
        return "api_key" in data and data["api_key"]
    
    def get_api_key(self) -> str:
        """Get stored API key"""
        data = self.load()
        return data.get("api_key", "")
    
    def set_api_key(self, key: str):
        """Store API key encrypted"""
        data = self.load()
        data["api_key"] = key
        self.save(data)
    
    def clear(self):
        """Clear all stored data"""
        if self.data_file.exists():
            self.data_file.unlink()
