"""
High-Performance DataFeed Service

Optimized WebSocket-based data feed with connection pooling,
automatic reconnection, and efficient tick processing.
"""

import asyncio
import threading
import time
import logging
import queue
from typing import Dict, List, Set, Optional, Callable, Any
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from kiteconnect import KiteTicker
from ..utils.config import config
from .tick_data import TickData, RingBuffer, TickStorage, TickAggregator, PerformanceMonitor

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Manages multiple WebSocket connections to maximize throughput
    """
    
    def __init__(self, api_key: str, access_token: str, max_connections: int = 3):
        """Initialize connection pool"""
        self.api_key = api_key
        self.access_token = access_token
        self.max_connections = max_connections
        self.connections = []
        self.connection_assignments = {}  # instrument_token -> connection_index
        self.instrument_counts = [0] * max_connections  # Track instruments per connection
        self.lock = threading.RLock()
        
        # Create connections
        for i in range(max_connections):
            ticker = KiteTicker(api_key, access_token)
            self.connections.append({
                'ticker': ticker,
                'instruments': set(),
                'connected': False,
                'reconnect_count': 0
            })
    
    def assign_instrument(self, instrument_token: int) -> int:
        """Assign instrument to least loaded connection"""
        with self.lock:
            # Find connection with minimum instruments
            min_count = min(self.instrument_counts)
            connection_index = self.instrument_counts.index(min_count)
            
            # Assign instrument
            self.connection_assignments[instrument_token] = connection_index
            self.connections[connection_index]['instruments'].add(instrument_token)
            self.instrument_counts[connection_index] += 1
            
            return connection_index
    
    def remove_instrument(self, instrument_token: int):
        """Remove instrument from its assigned connection"""
        with self.lock:
            if instrument_token in self.connection_assignments:
                connection_index = self.connection_assignments[instrument_token]
                self.connections[connection_index]['instruments'].discard(instrument_token)
                self.instrument_counts[connection_index] -= 1
                del self.connection_assignments[instrument_token]
    
    def get_connection(self, instrument_token: int) -> Optional[Dict]:
        """Get connection for specific instrument"""
        with self.lock:
            if instrument_token in self.connection_assignments:
                connection_index = self.connection_assignments[instrument_token]
                return self.connections[connection_index]
        return None
    
    def get_all_connections(self) -> List[Dict]:
        """Get all connections"""
        return self.connections.copy()


class DataFeedService:
    """
    High-performance data feed service with WebSocket connection pooling
    """
    
    def __init__(self, api_key: str, access_token: str):
        """Initialize data feed service"""
        self.api_key = api_key
        self.access_token = access_token
        
        # Configuration
        self.config = config
        self.max_connections = self.config.kite.max_connections
        self.max_instruments_per_connection = self.config.kite.max_instruments_per_connection
        
        # Connection management
        self.connection_pool = ConnectionPool(api_key, access_token, self.max_connections)
        
        # Data structures
        self.ring_buffer = RingBuffer(self.config.performance.ring_buffer_size)
        self.tick_storage = None
        self.tick_aggregator = TickAggregator(self.config.performance.tick_aggregation_interval)
        self.performance_monitor = PerformanceMonitor()
        
        # Subscription management
        self.subscribed_instruments = set()
        self.instrument_modes = {}  # instrument_token -> mode
        self.tick_callbacks = []  # List of callback functions
        
        # Threading
        self.running = False
        self.worker_pool = ThreadPoolExecutor(max_workers=self.config.performance.worker_threads)
        self.tick_queue = queue.Queue(maxsize=self.config.performance.buffer_size)
        
        # Statistics
        self.stats = {
            'total_ticks': 0,
            'ticks_per_second': 0,
            'connected_instruments': 0,
            'active_connections': 0,
            'last_tick_time': 0
        }
        
        # Initialize storage if enabled
        if self.config.datafeed.store_ticks:
            storage_path = f"data/processed/ticks_{int(time.time())}.bin"
            self.tick_storage = TickStorage(storage_path, self.config.performance.mmap_size)
        
        logger.info("DataFeed service initialized")
    
    def add_tick_callback(self, callback: Callable[[TickData], None]):
        """Add callback function to be called on each tick"""
        self.tick_callbacks.append(callback)
    
    def subscribe(self, instruments: List[int], mode: str = "quote") -> bool:
        """
        Subscribe to instruments with specified mode
        
        Args:
            instruments: List of instrument tokens
            mode: 'ltp', 'quote', or 'full'
        """
        try:
            # Validate mode
            if mode not in ['ltp', 'quote', 'full']:
                raise ValueError(f"Invalid mode: {mode}. Must be 'ltp', 'quote', or 'full'")
            
            # Check total instrument limit
            total_instruments = len(self.subscribed_instruments) + len(instruments)
            max_total = self.max_connections * self.max_instruments_per_connection
            
            if total_instruments > max_total:
                logger.error(f"Cannot subscribe to {len(instruments)} instruments. "
                           f"Would exceed limit of {max_total}")
                return False
            
            # Assign instruments to connections
            for instrument_token in instruments:
                if instrument_token not in self.subscribed_instruments:
                    connection_index = self.connection_pool.assign_instrument(instrument_token)
                    self.instrument_modes[instrument_token] = mode
                    self.subscribed_instruments.add(instrument_token)
                    
                    logger.debug(f"Assigned instrument {instrument_token} to connection {connection_index}")
            
            # Subscribe on each connection
            self._update_subscriptions()
            
            logger.info(f"Subscribed to {len(instruments)} instruments in {mode} mode")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to instruments: {e}")
            return False
    
    def unsubscribe(self, instruments: List[int]) -> bool:
        """Unsubscribe from instruments"""
        try:
            for instrument_token in instruments:
                if instrument_token in self.subscribed_instruments:
                    self.connection_pool.remove_instrument(instrument_token)
                    self.subscribed_instruments.remove(instrument_token)
                    del self.instrument_modes[instrument_token]
            
            # Update subscriptions on connections
            self._update_subscriptions()
            
            logger.info(f"Unsubscribed from {len(instruments)} instruments")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from instruments: {e}")
            return False
    
    def _update_subscriptions(self):
        """Update subscriptions on all connections"""
        for i, connection in enumerate(self.connection_pool.get_all_connections()):
            if connection['instruments'] and connection['connected']:
                ticker = connection['ticker']
                instruments = list(connection['instruments'])
                
                # Subscribe to instruments
                ticker.subscribe(instruments)
                
                # Set modes
                mode_groups = defaultdict(list)
                for instrument_token in instruments:
                    mode = self.instrument_modes.get(instrument_token, 'quote')
                    mode_groups[mode].append(instrument_token)
                
                for mode, tokens in mode_groups.items():
                    if mode == 'ltp':
                        ticker.set_mode(ticker.MODE_LTP, tokens)
                    elif mode == 'quote':
                        ticker.set_mode(ticker.MODE_QUOTE, tokens)
                    elif mode == 'full':
                        ticker.set_mode(ticker.MODE_FULL, tokens)
                
                logger.debug(f"Updated subscriptions for connection {i}: {len(instruments)} instruments")
    
    def start(self) -> bool:
        """Start the data feed service"""
        try:
            self.running = True
            
            # Start tick processing thread
            threading.Thread(target=self._tick_processor, daemon=True).start()
            
            # Start performance monitoring
            threading.Thread(target=self._performance_monitor, daemon=True).start()
            
            # Connect all WebSocket connections
            for i, connection in enumerate(self.connection_pool.get_all_connections()):
                self._setup_connection_callbacks(connection, i)
                threading.Thread(target=self._connect_websocket, args=(connection, i), daemon=True).start()
            
            logger.info("DataFeed service started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start DataFeed service: {e}")
            return False
    
    def stop(self):
        """Stop the data feed service"""
        try:
            self.running = False
            
            # Close all connections
            for connection in self.connection_pool.get_all_connections():
                if connection['connected']:
                    connection['ticker'].close()
            
            # Shutdown worker pool
            self.worker_pool.shutdown(wait=True)
            
            # Close storage
            if self.tick_storage:
                self.tick_storage.close()
            
            logger.info("DataFeed service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping DataFeed service: {e}")
    
    def _setup_connection_callbacks(self, connection: Dict, connection_index: int):
        """Setup callbacks for WebSocket connection"""
        ticker = connection['ticker']
        
        def on_ticks(ws, ticks):
            """Handle incoming ticks"""
            for tick_data in ticks:
                try:
                    # Convert to optimized TickData structure
                    tick = TickData(
                        instrument_token=tick_data.get('instrument_token', 0),
                        timestamp=int(time.time() * 1000),  # Current timestamp in ms
                        last_price=tick_data.get('last_price', 0.0),
                        volume=tick_data.get('volume', 0),
                        open_price=tick_data.get('ohlc', {}).get('open', 0.0),
                        high_price=tick_data.get('ohlc', {}).get('high', 0.0),
                        low_price=tick_data.get('ohlc', {}).get('low', 0.0),
                        prev_close=tick_data.get('ohlc', {}).get('close', 0.0),
                        change=tick_data.get('change', 0.0),
                        change_percent=tick_data.get('change_percent', 0.0),
                        exchange_timestamp=tick_data.get('exchange_timestamp', 0)
                    )
                    
                    # Queue tick for processing
                    if not self.tick_queue.full():
                        self.tick_queue.put((tick, connection_index))
                    else:
                        logger.warning("Tick queue full, dropping tick")
                        
                except Exception as e:
                    logger.error(f"Error processing tick: {e}")
        
        def on_connect(ws, response):
            """Handle connection established"""
            connection['connected'] = True
            connection['reconnect_count'] = 0
            logger.info(f"Connection {connection_index} established")
            
            # Subscribe to assigned instruments
            if connection['instruments']:
                self._update_subscriptions()
        
        def on_close(ws, code, reason):
            """Handle connection closed"""
            connection['connected'] = False
            logger.warning(f"Connection {connection_index} closed: {code} - {reason}")
        
        def on_error(ws, code, reason):
            """Handle connection error"""
            logger.error(f"Connection {connection_index} error: {code} - {reason}")
        
        def on_reconnect(ws, attempts_count):
            """Handle reconnection attempt"""
            connection['reconnect_count'] = attempts_count
            logger.info(f"Connection {connection_index} reconnecting: attempt {attempts_count}")
        
        def on_noreconnect(ws):
            """Handle failed reconnection"""
            connection['connected'] = False
            logger.error(f"Connection {connection_index} failed to reconnect")
        
        # Assign callbacks
        ticker.on_ticks = on_ticks
        ticker.on_connect = on_connect
        ticker.on_close = on_close
        ticker.on_error = on_error
        ticker.on_reconnect = on_reconnect
        ticker.on_noreconnect = on_noreconnect
    
    def _connect_websocket(self, connection: Dict, connection_index: int):
        """Connect WebSocket in separate thread"""
        try:
            ticker = connection['ticker']
            ticker.connect(threaded=True)
        except Exception as e:
            logger.error(f"Failed to connect WebSocket {connection_index}: {e}")
    
    def _tick_processor(self):
        """Process ticks from queue in separate thread"""
        while self.running:
            try:
                # Get tick from queue with timeout
                tick, connection_index = self.tick_queue.get(timeout=1.0)
                
                start_time = time.time()
                
                # Process tick
                self._process_tick(tick)
                
                # Record performance
                processing_time = time.time() - start_time
                self.performance_monitor.record_tick(tick.instrument_token, processing_time)
                
                # Update statistics
                self.stats['total_ticks'] += 1
                self.stats['last_tick_time'] = tick.timestamp
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in tick processor: {e}")
    
    def _process_tick(self, tick: TickData):
        """Process individual tick"""
        try:
            # Add to ring buffer
            self.ring_buffer.push(tick)
            
            # Store to file if enabled
            if self.tick_storage:
                tick_array = np.array([tick], dtype=self.ring_buffer.data.dtype)
                self.worker_pool.submit(self.tick_storage.write_ticks, tick_array)
            
            # Process aggregation
            completed_bar = self.tick_aggregator.process_tick(tick)
            if completed_bar:
                logger.debug(f"Completed bar for {tick.instrument_token}: {completed_bar}")
            
            # Call user callbacks
            for callback in self.tick_callbacks:
                try:
                    self.worker_pool.submit(callback, tick)
                except Exception as e:
                    logger.error(f"Error in tick callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
    
    def _performance_monitor(self):
        """Monitor performance metrics"""
        last_time = time.time()
        last_tick_count = 0
        
        while self.running:
            try:
                time.sleep(self.config.logging.performance_interval)
                
                current_time = time.time()
                current_tick_count = self.stats['total_ticks']
                
                # Calculate ticks per second
                elapsed = current_time - last_time
                tick_delta = current_tick_count - last_tick_count
                
                if elapsed > 0:
                    self.stats['ticks_per_second'] = tick_delta / elapsed
                
                # Update connection statistics
                active_connections = sum(1 for conn in self.connection_pool.get_all_connections() 
                                       if conn['connected'])
                self.stats['active_connections'] = active_connections
                self.stats['connected_instruments'] = len(self.subscribed_instruments)
                
                # Get performance stats
                perf_stats = self.performance_monitor.get_stats()
                
                # Log performance metrics
                logger.info(f"Performance: {self.stats['ticks_per_second']:.1f} ticks/sec, "
                          f"{active_connections}/{self.max_connections} connections, "
                          f"{len(self.subscribed_instruments)} instruments, "
                          f"avg processing: {perf_stats.get('avg_processing_time', 0):.4f}ms")
                
                last_time = current_time
                last_tick_count = current_tick_count
                
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
    
    def get_latest_ticks(self, instrument_token: int, count: int = 100) -> np.ndarray:
        """Get latest ticks for instrument"""
        return self.ring_buffer.get_by_instrument(instrument_token, count)
    
    def get_ohlc_bars(self, instrument_token: int, count: int = 100) -> List[Dict]:
        """Get latest OHLC bars for instrument"""
        return self.tick_aggregator.get_bars(instrument_token, count)
    
    def get_current_bar(self, instrument_token: int) -> Optional[Dict]:
        """Get current incomplete bar for instrument"""
        return self.tick_aggregator.get_current_bar(instrument_token)
    
    def get_statistics(self) -> Dict:
        """Get service statistics"""
        perf_stats = self.performance_monitor.get_stats()
        
        return {
            **self.stats,
            'performance': perf_stats,
            'queue_size': self.tick_queue.qsize(),
            'buffer_usage': self.ring_buffer.count / self.ring_buffer.size,
            'subscribed_instruments': len(self.subscribed_instruments)
        }