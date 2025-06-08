"""
Optimized Tick Data Structures

High-performance data structures for tick data storage and processing
using NumPy structured arrays and memory-mapped files.
"""

import numpy as np
import mmap
import os
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
import threading
import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class TickData(NamedTuple):
    """Optimized tick data structure"""
    instrument_token: int
    timestamp: int  # Unix timestamp in milliseconds
    last_price: float
    volume: int
    open_price: float
    high_price: float
    low_price: float
    prev_close: float
    change: float
    change_percent: float
    exchange_timestamp: int


# NumPy structured array dtype for tick data
TICK_DTYPE = np.dtype([
    ('instrument_token', np.uint32),
    ('timestamp', np.uint64),
    ('last_price', np.float32),
    ('volume', np.uint32),
    ('open_price', np.float32),
    ('high_price', np.float32),
    ('low_price', np.float32),
    ('prev_close', np.float32),
    ('change', np.float32),
    ('change_percent', np.float32),
    ('exchange_timestamp', np.uint64),
    ('bid_price', np.float32),
    ('ask_price', np.float32),
    ('bid_qty', np.uint32),
    ('ask_qty', np.uint32),
    ('oi', np.uint32),  # Open Interest
])


class RingBuffer:
    """
    High-performance ring buffer for tick data using pre-allocated NumPy arrays
    """
    
    def __init__(self, size: int):
        """Initialize ring buffer with given size"""
        self.size = size
        self.data = np.zeros(size, dtype=TICK_DTYPE)
        self.head = 0
        self.tail = 0
        self.count = 0
        self.lock = threading.RLock()
    
    def push(self, tick: TickData) -> bool:
        """
        Add tick data to buffer
        Returns True if successful, False if buffer is full
        """
        with self.lock:
            if self.count >= self.size:
                # Buffer is full, overwrite oldest data
                self.tail = (self.tail + 1) % self.size
            else:
                self.count += 1
            
            # Convert TickData to structured array format
            self.data[self.head] = (
                tick.instrument_token,
                tick.timestamp,
                tick.last_price,
                tick.volume,
                tick.open_price,
                tick.high_price,
                tick.low_price,
                tick.prev_close,
                tick.change,
                tick.change_percent,
                tick.exchange_timestamp,
                0.0,  # bid_price - filled by market depth if available
                0.0,  # ask_price
                0,    # bid_qty
                0,    # ask_qty
                0     # oi
            )
            
            self.head = (self.head + 1) % self.size
            return True
    
    def get_latest(self, count: int = 1) -> np.ndarray:
        """Get latest N ticks"""
        with self.lock:
            if self.count == 0:
                return np.array([], dtype=TICK_DTYPE)
            
            count = min(count, self.count)
            indices = []
            
            for i in range(count):
                idx = (self.head - 1 - i) % self.size
                indices.append(idx)
            
            return self.data[indices[::-1]]  # Reverse to get chronological order
    
    def get_by_instrument(self, instrument_token: int, count: int = 100) -> np.ndarray:
        """Get latest ticks for specific instrument"""
        with self.lock:
            if self.count == 0:
                return np.array([], dtype=TICK_DTYPE)
            
            # Find all ticks for this instrument
            mask = self.data['instrument_token'] == instrument_token
            matching_ticks = self.data[mask]
            
            if len(matching_ticks) == 0:
                return np.array([], dtype=TICK_DTYPE)
            
            # Sort by timestamp and return latest
            sorted_ticks = np.sort(matching_ticks, order='timestamp')
            return sorted_ticks[-count:] if len(sorted_ticks) >= count else sorted_ticks
    
    def clear(self):
        """Clear all data from buffer"""
        with self.lock:
            self.head = 0
            self.tail = 0
            self.count = 0
            self.data.fill(0)


class TickStorage:
    """
    High-performance tick data storage using memory-mapped files
    """
    
    def __init__(self, storage_path: str, max_size: int = 100000000):  # 100MB default
        """Initialize tick storage"""
        self.storage_path = storage_path
        self.max_size = max_size
        self.mmap_file = None
        self.file_handle = None
        self.lock = threading.RLock()
        
        # Create storage directory if it doesn't exist
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Initialize memory-mapped file
        self._init_mmap()
    
    def _init_mmap(self):
        """Initialize memory-mapped file"""
        try:
            # Create or open file
            self.file_handle = open(self.storage_path, 'r+b')
            
            # Get current file size
            file_size = os.path.getsize(self.storage_path)
            
            if file_size < self.max_size:
                # Extend file to max size
                self.file_handle.seek(self.max_size - 1)
                self.file_handle.write(b'\0')
                self.file_handle.flush()
            
            # Create memory map
            self.mmap_file = mmap.mmap(self.file_handle.fileno(), self.max_size)
            
        except FileNotFoundError:
            # Create new file
            with open(self.storage_path, 'wb') as f:
                f.write(b'\0' * self.max_size)
            
            # Retry initialization
            self.file_handle = open(self.storage_path, 'r+b')
            self.mmap_file = mmap.mmap(self.file_handle.fileno(), self.max_size)
        
        logger.info(f"Initialized tick storage: {self.storage_path}")
    
    def write_ticks(self, ticks: np.ndarray, offset: int = 0) -> int:
        """
        Write tick data to memory-mapped file
        Returns number of bytes written
        """
        with self.lock:
            if self.mmap_file is None:
                return 0
            
            # Convert to bytes
            tick_bytes = ticks.tobytes()
            bytes_to_write = len(tick_bytes)
            
            # Check if we have enough space
            if offset + bytes_to_write > self.max_size:
                logger.warning("Tick storage full, wrapping around")
                offset = 0
            
            # Write to memory-mapped file
            self.mmap_file.seek(offset)
            self.mmap_file.write(tick_bytes)
            self.mmap_file.flush()
            
            return bytes_to_write
    
    def read_ticks(self, offset: int = 0, count: int = 1000) -> np.ndarray:
        """Read tick data from memory-mapped file"""
        with self.lock:
            if self.mmap_file is None:
                return np.array([], dtype=TICK_DTYPE)
            
            bytes_per_tick = TICK_DTYPE.itemsize
            bytes_to_read = count * bytes_per_tick
            
            # Check bounds
            if offset + bytes_to_read > self.max_size:
                bytes_to_read = self.max_size - offset
                count = bytes_to_read // bytes_per_tick
            
            # Read from memory-mapped file
            self.mmap_file.seek(offset)
            tick_bytes = self.mmap_file.read(bytes_to_read)
            
            # Convert back to structured array
            return np.frombuffer(tick_bytes, dtype=TICK_DTYPE, count=count)
    
    def close(self):
        """Close storage and clean up resources"""
        with self.lock:
            if self.mmap_file:
                self.mmap_file.close()
                self.mmap_file = None
            
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None


class TickAggregator:
    """
    High-performance tick aggregation for OHLCV calculations
    """
    
    def __init__(self, aggregation_interval: int = 1000):  # 1 second default
        """Initialize tick aggregator"""
        self.aggregation_interval = aggregation_interval  # milliseconds
        self.current_bars = {}  # instrument_token -> current bar data
        self.completed_bars = defaultdict(list)  # instrument_token -> list of completed bars
        self.lock = threading.RLock()
    
    def process_tick(self, tick: TickData) -> Optional[Dict]:
        """
        Process incoming tick and return completed bar if interval elapsed
        """
        with self.lock:
            instrument_token = tick.instrument_token
            
            # Calculate bar timestamp (aligned to interval)
            bar_timestamp = (tick.timestamp // self.aggregation_interval) * self.aggregation_interval
            
            # Get or create current bar
            if instrument_token not in self.current_bars:
                self.current_bars[instrument_token] = {
                    'instrument_token': instrument_token,
                    'timestamp': bar_timestamp,
                    'open': tick.last_price,
                    'high': tick.last_price,
                    'low': tick.last_price,
                    'close': tick.last_price,
                    'volume': tick.volume,
                    'tick_count': 1
                }
                return None
            
            current_bar = self.current_bars[instrument_token]
            
            # Check if we need to start a new bar
            if bar_timestamp > current_bar['timestamp']:
                # Complete current bar
                completed_bar = current_bar.copy()
                self.completed_bars[instrument_token].append(completed_bar)
                
                # Start new bar
                self.current_bars[instrument_token] = {
                    'instrument_token': instrument_token,
                    'timestamp': bar_timestamp,
                    'open': tick.last_price,
                    'high': tick.last_price,
                    'low': tick.last_price,
                    'close': tick.last_price,
                    'volume': tick.volume,
                    'tick_count': 1
                }
                
                return completed_bar
            
            # Update current bar
            current_bar['high'] = max(current_bar['high'], tick.last_price)
            current_bar['low'] = min(current_bar['low'], tick.last_price)
            current_bar['close'] = tick.last_price
            current_bar['volume'] += tick.volume
            current_bar['tick_count'] += 1
            
            return None
    
    def get_bars(self, instrument_token: int, count: int = 100) -> List[Dict]:
        """Get latest completed bars for instrument"""
        with self.lock:
            bars = self.completed_bars.get(instrument_token, [])
            return bars[-count:] if len(bars) >= count else bars
    
    def get_current_bar(self, instrument_token: int) -> Optional[Dict]:
        """Get current incomplete bar for instrument"""
        with self.lock:
            return self.current_bars.get(instrument_token)


class PerformanceMonitor:
    """
    Monitor tick processing performance
    """
    
    def __init__(self):
        """Initialize performance monitor"""
        self.tick_counts = defaultdict(int)
        self.processing_times = defaultdict(list)
        self.last_reset = time.time()
        self.lock = threading.RLock()
    
    def record_tick(self, instrument_token: int, processing_time: float):
        """Record tick processing metrics"""
        with self.lock:
            self.tick_counts[instrument_token] += 1
            self.processing_times[instrument_token].append(processing_time)
            
            # Keep only last 1000 processing times per instrument
            if len(self.processing_times[instrument_token]) > 1000:
                self.processing_times[instrument_token] = self.processing_times[instrument_token][-1000:]
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_reset
            
            total_ticks = sum(self.tick_counts.values())
            
            stats = {
                'total_ticks': total_ticks,
                'ticks_per_second': total_ticks / elapsed if elapsed > 0 else 0,
                'elapsed_seconds': elapsed,
                'instruments_count': len(self.tick_counts),
                'avg_processing_time': 0.0,
                'max_processing_time': 0.0,
            }
            
            # Calculate processing time statistics
            all_times = []
            for times in self.processing_times.values():
                all_times.extend(times)
            
            if all_times:
                stats['avg_processing_time'] = np.mean(all_times)
                stats['max_processing_time'] = np.max(all_times)
                stats['p95_processing_time'] = np.percentile(all_times, 95)
                stats['p99_processing_time'] = np.percentile(all_times, 99)
            
            return stats
    
    def reset(self):
        """Reset performance counters"""
        with self.lock:
            self.tick_counts.clear()
            self.processing_times.clear()
            self.last_reset = time.time()