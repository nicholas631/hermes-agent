#!/usr/bin/env python3
"""
Name: scripts/monitor_test_memory.py
Description: Memory monitoring wrapper for multi-model testing with real-time VRAM and RAM checks.
Primary Functions:
  - Monitor VRAM usage via nvidia-smi
  - Monitor system RAM usage via psutil
  - Terminate test subprocess if memory thresholds exceeded
  - Log memory usage timeline throughout test execution
  - Generate JSON report with memory metrics
Revision: 0.1.1
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import psutil
except ImportError:
    print("ERROR: psutil not installed. Run: pip install psutil")
    sys.exit(1)


@dataclass
class MemorySample:
    """Single memory measurement sample."""
    timestamp: str
    vram_used_gb: float
    vram_total_gb: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float


@dataclass
class MemoryReport:
    """Complete memory monitoring report."""
    test_command: str
    start_time: str
    end_time: str
    duration_seconds: float
    exit_code: int
    aborted: bool
    abort_reason: Optional[str]
    vram_threshold_gb: float
    ram_threshold_percent: float
    samples: list[MemorySample] = field(default_factory=list)
    peak_vram_gb: float = 0.0
    peak_ram_percent: float = 0.0
    avg_vram_gb: float = 0.0
    avg_ram_percent: float = 0.0


def check_vram_usage() -> tuple[float, float]:
    """
    Query GPU VRAM usage via nvidia-smi.
    
    Returns:
        (used_gb, total_gb) tuple
    """
    try:
        output = subprocess.check_output([
            "nvidia-smi",
            "--query-gpu=memory.used,memory.total",
            "--format=csv,noheader,nounits"
        ], text=True, stderr=subprocess.DEVNULL)
        
        used, total = map(float, output.strip().split(","))
        return used / 1024, total / 1024  # Convert MB to GB
    except Exception as exc:
        print(f"WARNING: Failed to query VRAM: {exc}")
        return 0.0, 24.0  # Return safe defaults


def check_system_ram() -> tuple[float, float, float]:
    """
    Query system RAM usage via psutil.
    
    Returns:
        (percent, used_gb, total_gb) tuple
    """
    try:
        mem = psutil.virtual_memory()
        return mem.percent, mem.used / (1024**3), mem.total / (1024**3)
    except Exception as exc:
        print(f"WARNING: Failed to query system RAM: {exc}")
        return 0.0, 0.0, 64.0  # Return safe defaults


def should_abort(
    vram_gb: float,
    ram_percent: float,
    vram_threshold: float,
    ram_threshold: float
) -> tuple[bool, str]:
    """
    Check if test should abort due to memory pressure.
    
    Args:
        vram_gb: Current VRAM usage in GB
        ram_percent: Current system RAM usage percentage
        vram_threshold: VRAM threshold in GB
        ram_threshold: RAM threshold percentage
        
    Returns:
        (should_abort, reason) tuple
    """
    if vram_gb > vram_threshold:
        return True, f"VRAM exceeded threshold: {vram_gb:.1f}GB > {vram_threshold}GB"
    if ram_percent > ram_threshold:
        return True, f"System RAM exceeded threshold: {ram_percent:.1f}% > {ram_threshold}%"
    return False, ""


class MemoryMonitor:
    """Background memory monitor with threshold checking."""
    
    def __init__(
        self,
        vram_threshold_gb: float,
        ram_threshold_percent: float,
        sample_interval: float = 2.0
    ):
        self.vram_threshold_gb = vram_threshold_gb
        self.ram_threshold_percent = ram_threshold_percent
        self.sample_interval = sample_interval
        
        self.samples: list[MemorySample] = []
        self.aborted = False
        self.abort_reason = ""
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            # Sample memory
            vram_used, vram_total = check_vram_usage()
            ram_percent, ram_used, ram_total = check_system_ram()
            
            sample = MemorySample(
                timestamp=datetime.now().isoformat(),
                vram_used_gb=round(vram_used, 2),
                vram_total_gb=round(vram_total, 2),
                ram_percent=round(ram_percent, 1),
                ram_used_gb=round(ram_used, 2),
                ram_total_gb=round(ram_total, 2),
            )
            self.samples.append(sample)
            
            # Check thresholds
            should_stop, reason = should_abort(
                vram_used,
                ram_percent,
                self.vram_threshold_gb,
                self.ram_threshold_percent
            )
            
            if should_stop:
                self.aborted = True
                self.abort_reason = reason
                print(f"\nWARNING: MEMORY THRESHOLD EXCEEDED: {reason}")
                self.running = False
                break
            
            time.sleep(self.sample_interval)
    
    def start(self):
        """Start monitoring in background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
    
    def get_stats(self) -> dict:
        """Calculate statistics from samples."""
        if not self.samples:
            return {
                "peak_vram_gb": 0.0,
                "peak_ram_percent": 0.0,
                "avg_vram_gb": 0.0,
                "avg_ram_percent": 0.0,
            }
        
        vram_values = [s.vram_used_gb for s in self.samples]
        ram_values = [s.ram_percent for s in self.samples]
        
        return {
            "peak_vram_gb": round(max(vram_values), 2),
            "peak_ram_percent": round(max(ram_values), 1),
            "avg_vram_gb": round(sum(vram_values) / len(vram_values), 2),
            "avg_ram_percent": round(sum(ram_values) / len(ram_values), 1),
        }


def run_monitored_test(
    command: list[str],
    vram_threshold_gb: float,
    ram_threshold_percent: float,
    output_file: Optional[Path] = None,
    verbose: bool = False
) -> MemoryReport:
    """
    Run a test command with memory monitoring.
    
    Args:
        command: Command to execute as list of strings
        vram_threshold_gb: VRAM threshold in GB
        ram_threshold_percent: RAM threshold percentage
        output_file: Optional output file for JSON report
        verbose: Print detailed monitoring info
        
    Returns:
        MemoryReport with test results and memory metrics
    """
    start_time = datetime.now()
    
    # Create monitor
    monitor = MemoryMonitor(vram_threshold_gb, ram_threshold_percent)
    
    print(f"Starting monitored test: {' '.join(command)}")
    print(f"Memory thresholds: VRAM {vram_threshold_gb}GB, RAM {ram_threshold_percent}%")
    print(f"Monitoring every 2 seconds...")
    print()
    
    # Start monitoring
    monitor.start()
    
    # Run test subprocess
    try:
        # Always stream output to avoid pipe buffer deadlock
        # When verbose=False, output still goes to terminal but we don't capture it
        process = subprocess.Popen(
            command,
            stdout=None,  # Stream to terminal
            stderr=None,  # Stream to terminal
            text=True
        )
        
        # Wait for completion or abort
        while process.poll() is None:
            if monitor.aborted:
                print("Terminating test process due to memory threshold violation...")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
                break
            time.sleep(0.5)
        
        exit_code = process.wait()
        
    except Exception as exc:
        print(f"ERROR running test: {exc}")
        exit_code = 1
    finally:
        monitor.stop()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Build report
    stats = monitor.get_stats()
    
    report = MemoryReport(
        test_command=" ".join(command),
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        duration_seconds=round(duration, 1),
        exit_code=exit_code,
        aborted=monitor.aborted,
        abort_reason=monitor.abort_reason if monitor.aborted else None,
        vram_threshold_gb=vram_threshold_gb,
        ram_threshold_percent=ram_threshold_percent,
        samples=monitor.samples,
        peak_vram_gb=stats["peak_vram_gb"],
        peak_ram_percent=stats["peak_ram_percent"],
        avg_vram_gb=stats["avg_vram_gb"],
        avg_ram_percent=stats["avg_ram_percent"],
    )
    
    # Print summary
    print()
    print("=" * 70)
    print("MEMORY MONITORING SUMMARY")
    print("=" * 70)
    print(f"Duration:        {duration:.1f} seconds")
    print(f"Exit Code:       {exit_code}")
    print(f"Aborted:         {monitor.aborted}")
    if monitor.aborted:
        print(f"Abort Reason:    {monitor.abort_reason}")
    print()
    print(f"Peak VRAM:       {stats['peak_vram_gb']:.2f} GB (threshold: {vram_threshold_gb} GB)")
    print(f"Peak RAM:        {stats['peak_ram_percent']:.1f}% (threshold: {ram_threshold_percent}%)")
    print(f"Avg VRAM:        {stats['avg_vram_gb']:.2f} GB")
    print(f"Avg RAM:         {stats['avg_ram_percent']:.1f}%")
    print(f"Samples:         {len(monitor.samples)}")
    print("=" * 70)
    
    # Save JSON report
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)
        print(f"\nMemory report saved to: {output_file}")
    
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a test command with memory monitoring and threshold checks"
    )
    
    parser.add_argument(
        "command",
        nargs="+",
        help="Command to execute (e.g., python script.py --arg value)"
    )
    parser.add_argument(
        "--vram-threshold",
        type=float,
        default=23.0,
        help="VRAM threshold in GB (default: 23.0)"
    )
    parser.add_argument(
        "--ram-threshold",
        type=float,
        default=90.0,
        help="System RAM threshold percentage (default: 90.0)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for JSON memory report"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show test command output in real-time"
    )
    
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point."""
    args = parse_args(argv or sys.argv[1:])
    
    # Run monitored test
    report = run_monitored_test(
        command=args.command,
        vram_threshold_gb=args.vram_threshold,
        ram_threshold_percent=args.ram_threshold,
        output_file=args.output,
        verbose=args.verbose
    )
    
    # Return exit code based on test result and memory status
    if report.aborted:
        return 2  # Memory threshold violation
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
