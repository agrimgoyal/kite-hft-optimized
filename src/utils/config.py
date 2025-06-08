"""
Optimized Configuration Manager

High-performance configuration management with environment variable support,
validation, and type safety.
"""

import os
import yaml
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class KiteConfig:
    """Kite Connect API configuration"""
    api_key: str = ""
    api_secret: str = ""
    user_id: str = ""
    password: str = ""
    totp_secret: str = ""
    
    # Rate limits
    http_rate_limit: int = 3
    historical_rate_limit: int = 2
    order_rate_limit: int = 200
    max_orders_per_day: int = 3000
    
    # WebSocket settings
    max_connections: int = 3
    max_instruments_per_connection: int = 3000
    reconnect_delay: int = 5
    max_reconnect_attempts: int = 50
    ping_interval: int = 30


@dataclass
class PerformanceConfig:
    """Performance optimization settings"""
    buffer_size: int = 10000
    ring_buffer_size: int = 1000000
    worker_threads: int = 4
    io_threads: int = 2
    batch_size: int = 500
    tick_aggregation_interval: int = 100
    use_mmap: bool = True
    mmap_size: int = 100000000


@dataclass
class TradingConfig:
    """Trading parameters and limits"""
    market_start: str = "09:15:00"
    market_end: str = "15:30:00"
    pre_market: str = "09:00:00"
    default_quantity: int = 1
    max_position_size: int = 1000000
    risk_per_trade: float = 0.02
    order_timeout: int = 30
    order_retry_count: int = 3
    order_retry_delay: int = 1


@dataclass
class DataFeedConfig:
    """Data feed configuration"""
    primary_source: str = "websocket"
    equity_mode: str = "quote"
    futures_mode: str = "full"
    options_mode: str = "quote"
    auto_subscribe: bool = True
    subscription_batch_size: int = 100
    store_ticks: bool = True
    tick_storage_format: str = "binary"
    max_storage_days: int = 7


@dataclass
class RiskConfig:
    """Risk management parameters"""
    max_positions: int = 20
    max_sector_exposure: float = 0.3
    max_single_stock: float = 0.1
    default_stop_loss: float = 0.02
    trailing_stop: bool = True
    daily_loss_limit: float = 0.05
    drawdown_limit: float = 0.1


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_to_file: bool = True
    log_file: str = "logs/trading.log"
    max_log_size: int = 100000000
    backup_count: int = 5
    performance_logging: bool = True
    performance_interval: int = 300


class ConfigManager:
    """
    High-performance configuration manager with caching and validation
    """
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """Singleton pattern for global configuration access"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = {}
            self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file and environment variables"""
        try:
            # Get config file path
            config_path = self._get_config_path()
            
            # Load YAML configuration
            if config_path.exists():
                with open(config_path, 'r') as f:
                    yaml_config = yaml.safe_load(f) or {}
            else:
                logger.warning(f"Config file not found: {config_path}")
                yaml_config = {}
            
            # Override with environment variables
            self._config = self._merge_env_vars(yaml_config)
            
            # Validate configuration
            self._validate_config()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _get_config_path(self) -> Path:
        """Get configuration file path"""
        # Check environment variable first
        config_path = os.getenv('KITE_CONFIG_PATH')
        if config_path:
            return Path(config_path)
        
        # Default paths
        current_dir = Path(__file__).parent.parent.parent
        possible_paths = [
            current_dir / "config" / "config.yaml",
            current_dir / "config.yaml",
            Path.home() / ".kite" / "config.yaml"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Return default path even if it doesn't exist
        return current_dir / "config" / "config.yaml"
    
    def _merge_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge environment variables with YAML configuration"""
        # Kite API credentials from environment
        kite_config = config.setdefault('kite', {})
        
        env_mappings = {
            'KITE_API_KEY': ['kite', 'api_key'],
            'KITE_API_SECRET': ['kite', 'api_secret'],
            'KITE_USER_ID': ['kite', 'user_id'],
            'KITE_PASSWORD': ['kite', 'password'],
            'KITE_TOTP_SECRET': ['kite', 'totp_secret'],
            'KITE_LOG_LEVEL': ['logging', 'level'],
            'KITE_DEBUG': ['debug', 'enabled'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                # Navigate to nested config location
                current = config
                for key in config_path[:-1]:
                    current = current.setdefault(key, {})
                
                # Set the value with proper type conversion
                if env_var == 'KITE_DEBUG':
                    current[config_path[-1]] = value.lower() in ('true', '1', 'yes')
                else:
                    current[config_path[-1]] = value
        
        return config
    
    def _validate_config(self):
        """Validate critical configuration parameters"""
        kite_config = self._config.get('kite', {})
        
        # Check required Kite API credentials
        required_fields = ['api_key', 'api_secret', 'user_id', 'password', 'totp_secret']
        missing_fields = [field for field in required_fields if not kite_config.get(field)]
        
        if missing_fields:
            logger.error(f"Missing required Kite API credentials: {missing_fields}")
            logger.error("Set these via environment variables or config file")
            raise ValueError(f"Missing required configuration: {missing_fields}")
        
        # Validate numeric ranges
        performance_config = self._config.get('performance', {})
        if performance_config.get('worker_threads', 4) < 1:
            raise ValueError("worker_threads must be >= 1")
        
        trading_config = self._config.get('trading', {})
        if trading_config.get('risk_per_trade', 0.02) <= 0 or trading_config.get('risk_per_trade', 0.02) > 1:
            raise ValueError("risk_per_trade must be between 0 and 1")
        
        logger.debug("Configuration validation passed")
    
    @property
    def kite(self) -> KiteConfig:
        """Get Kite Connect configuration"""
        kite_data = self._config.get('kite', {})
        rate_limits = kite_data.get('rate_limits', {})
        websocket = kite_data.get('websocket', {})
        
        return KiteConfig(
            api_key=kite_data.get('api_key', ''),
            api_secret=kite_data.get('api_secret', ''),
            user_id=kite_data.get('user_id', ''),
            password=kite_data.get('password', ''),
            totp_secret=kite_data.get('totp_secret', ''),
            http_rate_limit=rate_limits.get('http_api', 3),
            historical_rate_limit=rate_limits.get('historical_api', 2),
            order_rate_limit=rate_limits.get('order_placement', 200),
            max_orders_per_day=rate_limits.get('max_orders_per_day', 3000),
            max_connections=websocket.get('max_connections', 3),
            max_instruments_per_connection=websocket.get('max_instruments_per_connection', 3000),
            reconnect_delay=websocket.get('reconnect_delay', 5),
            max_reconnect_attempts=websocket.get('max_reconnect_attempts', 50),
            ping_interval=websocket.get('ping_interval', 30)
        )
    
    @property
    def performance(self) -> PerformanceConfig:
        """Get performance configuration"""
        perf_data = self._config.get('performance', {})
        return PerformanceConfig(
            buffer_size=perf_data.get('buffer_size', 10000),
            ring_buffer_size=perf_data.get('ring_buffer_size', 1000000),
            worker_threads=perf_data.get('worker_threads', 4),
            io_threads=perf_data.get('io_threads', 2),
            batch_size=perf_data.get('batch_size', 500),
            tick_aggregation_interval=perf_data.get('tick_aggregation_interval', 100),
            use_mmap=perf_data.get('use_mmap', True),
            mmap_size=perf_data.get('mmap_size', 100000000)
        )
    
    @property
    def trading(self) -> TradingConfig:
        """Get trading configuration"""
        trading_data = self._config.get('trading', {})
        return TradingConfig(
            market_start=trading_data.get('market_start', '09:15:00'),
            market_end=trading_data.get('market_end', '15:30:00'),
            pre_market=trading_data.get('pre_market', '09:00:00'),
            default_quantity=trading_data.get('default_quantity', 1),
            max_position_size=trading_data.get('max_position_size', 1000000),
            risk_per_trade=trading_data.get('risk_per_trade', 0.02),
            order_timeout=trading_data.get('order_timeout', 30),
            order_retry_count=trading_data.get('order_retry_count', 3),
            order_retry_delay=trading_data.get('order_retry_delay', 1)
        )
    
    @property
    def datafeed(self) -> DataFeedConfig:
        """Get data feed configuration"""
        datafeed_data = self._config.get('datafeed', {})
        return DataFeedConfig(
            primary_source=datafeed_data.get('primary_source', 'websocket'),
            equity_mode=datafeed_data.get('equity_mode', 'quote'),
            futures_mode=datafeed_data.get('futures_mode', 'full'),
            options_mode=datafeed_data.get('options_mode', 'quote'),
            auto_subscribe=datafeed_data.get('auto_subscribe', True),
            subscription_batch_size=datafeed_data.get('subscription_batch_size', 100),
            store_ticks=datafeed_data.get('store_ticks', True),
            tick_storage_format=datafeed_data.get('tick_storage_format', 'binary'),
            max_storage_days=datafeed_data.get('max_storage_days', 7)
        )
    
    @property
    def risk(self) -> RiskConfig:
        """Get risk management configuration"""
        risk_data = self._config.get('risk', {})
        return RiskConfig(
            max_positions=risk_data.get('max_positions', 20),
            max_sector_exposure=risk_data.get('max_sector_exposure', 0.3),
            max_single_stock=risk_data.get('max_single_stock', 0.1),
            default_stop_loss=risk_data.get('default_stop_loss', 0.02),
            trailing_stop=risk_data.get('trailing_stop', True),
            daily_loss_limit=risk_data.get('daily_loss_limit', 0.05),
            drawdown_limit=risk_data.get('drawdown_limit', 0.1)
        )
    
    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration"""
        logging_data = self._config.get('logging', {})
        return LoggingConfig(
            level=logging_data.get('level', 'INFO'),
            format=logging_data.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            log_to_file=logging_data.get('log_to_file', True),
            log_file=logging_data.get('log_file', 'logs/trading.log'),
            max_log_size=logging_data.get('max_log_size', 100000000),
            backup_count=logging_data.get('backup_count', 5),
            performance_logging=logging_data.get('performance_logging', True),
            performance_interval=logging_data.get('performance_interval', 300)
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def reload(self):
        """Reload configuration from file"""
        self._config = {}
        self._load_config()
        logger.info("Configuration reloaded")


# Global configuration instance
config = ConfigManager()