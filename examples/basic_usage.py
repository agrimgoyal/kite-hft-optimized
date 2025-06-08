#!/usr/bin/env python3
"""
Basic Usage Example for Kite HFT Optimized Trading System

This example demonstrates how to:
1. Set up authentication
2. Initialize the data feed
3. Subscribe to instruments
4. Process real-time ticks
5. Monitor performance
"""

import time
import logging
from typing import List

# Import our optimized modules
from src.auth.kite_auth import KiteAuthenticator
from src.datafeed.datafeed import DataFeedService
from src.datafeed.tick_data import TickData
from src.utils.config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BasicTradingExample:
    """
    Basic example of the optimized trading system
    """
    
    def __init__(self):
        """Initialize the trading system"""
        self.authenticator = None
        self.datafeed = None
        self.running = False
        
        # Example instruments (replace with your own)
        self.instruments = [
            738561,  # RELIANCE
            5633,    # ACC
            81153,   # SBIN
            2953217, # NIFTY 50
        ]
    
    def setup_authentication(self) -> bool:
        """Set up Kite authentication"""
        try:
            logger.info("Setting up authentication...")
            self.authenticator = KiteAuthenticator()
            
            if self.authenticator.authenticate():
                logger.info("✅ Authentication successful")
                return True
            else:
                logger.error("❌ Authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Authentication setup failed: {e}")
            return False
    
    def setup_datafeed(self) -> bool:
        """Set up the data feed service"""
        try:
            logger.info("Setting up data feed...")
            
            # Create data feed service
            self.datafeed = DataFeedService(
                api_key=config.kite.api_key,
                access_token=self.authenticator.get_access_token()
            )
            
            # Add our tick processing callback
            self.datafeed.add_tick_callback(self.process_tick)
            
            logger.info("✅ Data feed setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Data feed setup failed: {e}")
            return False
    
    def process_tick(self, tick: TickData):
        """
        Process individual ticks
        
        This is where you would implement your trading logic
        """
        try:
            # Example: Log significant price movements
            if abs(tick.change_percent) > 1.0:  # More than 1% change
                logger.info(
                    f"📈 Large move: {tick.instrument_token} "
                    f"Price: {tick.last_price:.2f} "
                    f"Change: {tick.change_percent:.2f}%"
                )
            
            # Example: Get latest bars for technical analysis
            current_bar = self.datafeed.get_current_bar(tick.instrument_token)
            if current_bar:
                # You could calculate indicators here
                # RSI, moving averages, etc.
                pass
            
            # Example: Check for trading signals
            if self.should_trade(tick):
                logger.info(f"🔔 Trading signal for {tick.instrument_token}")
                # Here you would place orders via execution module
                
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
    
    def should_trade(self, tick: TickData) -> bool:
        """
        Example trading logic
        
        Replace this with your actual strategy
        """
        # Very simple example: buy on 2% dip, sell on 2% gain
        return abs(tick.change_percent) > 2.0
    
    def start_trading(self):
        """Start the trading system"""
        try:
            logger.info("🚀 Starting trading system...")
            
            # Subscribe to instruments
            logger.info(f"Subscribing to {len(self.instruments)} instruments...")
            success = self.datafeed.subscribe(self.instruments, mode="quote")
            
            if not success:
                logger.error("Failed to subscribe to instruments")
                return False
            
            # Start data feed
            if not self.datafeed.start():
                logger.error("Failed to start data feed")
                return False
            
            self.running = True
            logger.info("✅ Trading system started successfully")
            
            # Monitor performance
            self.monitor_performance()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start trading system: {e}")
            return False
    
    def monitor_performance(self):
        """Monitor system performance"""
        logger.info("📊 Starting performance monitoring...")
        
        try:
            while self.running:
                # Wait 30 seconds between performance reports
                time.sleep(30)
                
                # Get statistics
                stats = self.datafeed.get_statistics()
                
                # Log performance metrics
                logger.info(
                    f"📊 Performance: "
                    f"{stats['ticks_per_second']:.1f} ticks/sec, "
                    f"{stats['active_connections']}/{config.kite.max_connections} connections, "
                    f"{stats['subscribed_instruments']} instruments, "
                    f"Buffer: {stats['buffer_usage']:.1%}"
                )
                
                # Example: Check for performance issues
                if stats['ticks_per_second'] < 10:
                    logger.warning("⚠️ Low tick rate detected")
                
                if stats['active_connections'] < config.kite.max_connections:
                    logger.warning("⚠️ Some WebSocket connections are down")
                
        except KeyboardInterrupt:
            logger.info("🛑 Stopping performance monitoring...")
            self.stop_trading()
        except Exception as e:
            logger.error(f"Performance monitoring error: {e}")
    
    def stop_trading(self):
        """Stop the trading system"""
        try:
            logger.info("🛑 Stopping trading system...")
            self.running = False
            
            if self.datafeed:
                self.datafeed.stop()
            
            logger.info("✅ Trading system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping trading system: {e}")
    
    def run(self):
        """Main entry point"""
        try:
            logger.info("🎯 Kite HFT Optimized Trading System")
            logger.info("=" * 50)
            
            # Step 1: Authentication
            if not self.setup_authentication():
                return False
            
            # Step 2: Data feed setup
            if not self.setup_datafeed():
                return False
            
            # Step 3: Start trading
            if not self.start_trading():
                return False
            
            return True
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Received interrupt signal")
            self.stop_trading()
        except Exception as e:
            logger.error(f"❌ System error: {e}")
            self.stop_trading()
            return False


def main():
    """Main function"""
    # Create and run trading system
    trading_system = BasicTradingExample()
    
    try:
        success = trading_system.run()
        if success:
            logger.info("✅ Trading system completed successfully")
        else:
            logger.error("❌ Trading system failed")
            return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())