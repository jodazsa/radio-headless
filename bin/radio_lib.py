#!/usr/bin/env python3
"""Shared utilities for radio-voice project.

This module provides common functionality used across encoder-controller,
oled-display, and radio-play scripts.
"""
import logging
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def setup_logging(name: str, log_file: Optional[Path] = None) -> logging.Logger:
    """Configure logging for a radio script.
    
    Args:
        name: Logger name (typically the script name)
        log_file: Optional path to log file. If None, only logs to console.
        
    Returns:
        Configured logger instance
        
    Example:
        logger = setup_logging('encoder-controller', Path('/home/radio/encoder.log'))
        logger.info("Starting up...")
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (captured by systemd journal)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Optional file handler for persistent logs
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # If file logging fails, just continue with console logging
            logger.warning(f"Could not create log file {log_file}: {e}")
    
    return logger


def parse_i2c_addr(v: Any) -> int:
    """Parse I2C address from various formats.
    
    Args:
        v: Address as int (0x49), hex string ("0x49"), or decimal string ("73")
        
    Returns:
        Integer I2C address
        
    Raises:
        TypeError: If v is not a supported type
        
    Examples:
        >>> parse_i2c_addr(0x49)
        73
        >>> parse_i2c_addr("0x49")
        73
        >>> parse_i2c_addr("73")
        73
    """
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        v = v.strip().lower()
        return int(v, 16) if v.startswith("0x") else int(v)
    raise TypeError(f"Unsupported I2C address type: {type(v)}")


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML file, return empty dict if file doesn't exist.
    
    Args:
        path: Path to YAML file
        
    Returns:
        Parsed YAML as dictionary, or empty dict if file not found
        
    Example:
        cfg = load_yaml(Path("/home/radio/hardware-config.yaml"))
    """
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}")


def read_state(state_path: Path) -> Dict[str, str]:
    """Read key=value state file.
    
    Args:
        state_path: Path to state file
        
    Returns:
        Dictionary of key-value pairs from state file
        
    Example:
        state = read_state(Path("/home/radio/.radio-state"))
        bank = int(state.get("current_bank", "0"))
    """
    st = {}
    if not state_path.exists():
        return st
    
    for line in state_path.read_text().splitlines():
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            st[k.strip()] = v.strip()
    return st


def write_state(state_path: Path, **kwargs) -> None:
    """Write state file, preserving existing keys not in kwargs.
    
    Args:
        state_path: Path to state file
        **kwargs: Key-value pairs to write/update
        
    Example:
        write_state(STATE_PATH, current_bank=0, current_station=3, last_volume=75)
    """
    # Read existing state to preserve keys we're not updating
    st = read_state(state_path)
    
    # Update with new values
    st.update({k: str(v) for k, v in kwargs.items()})
    
    # Write back
    out = "".join(f"{k}={v}\n" for k, v in st.items())
    state_path.write_text(out)


def sh(cmd, check=False) -> subprocess.CompletedProcess:
    """Run shell command and return result.
    
    Args:
        cmd: Command as list of strings
        check: If True, raise CalledProcessError on non-zero exit
        
    Returns:
        CompletedProcess with stdout, stderr, and returncode
        
    Example:
        result = sh(["mpc", "status"])
        if result.returncode == 0:
            print(result.stdout)
    """
    return subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        check=check
    )


def clamp(n: float, lo: float, hi: float) -> float:
    """Clamp value between min and max.
    
    Args:
        n: Value to clamp
        lo: Minimum value
        hi: Maximum value
        
    Returns:
        Value clamped to [lo, hi] range
        
    Examples:
        >>> clamp(5, 0, 10)
        5
        >>> clamp(-5, 0, 10)
        0
        >>> clamp(15, 0, 10)
        10
    """
    return lo if n < lo else hi if n > hi else n


def validate_hardware_config(cfg: Dict[str, Any]) -> list:
    """Validate hardware configuration and return list of errors.
    
    Args:
        cfg: Hardware config dictionary
        
    Returns:
        List of error messages (empty if valid)
        
    Example:
        errors = validate_hardware_config(cfg)
        if errors:
            for err in errors:
                print(f"Config error: {err}")
    """
    errors = []

    if not isinstance(cfg, dict):
        return ["Hardware config must be a dictionary"]
    
    # Check required sections exist
    if "i2c" not in cfg:
        errors.append("Missing 'i2c' section")
    else:
        i2c = cfg["i2c"]
        if "encoder_i2c_address" not in i2c:
            errors.append("Missing i2c.encoder_i2c_address")
        if "oled_i2c_address" not in i2c:
            errors.append("Missing i2c.oled_i2c_address")
    
    if "encoders" not in cfg:
        errors.append("Missing 'encoders' section")
    
    if "controls" not in cfg:
        errors.append("Missing 'controls' section")
    else:
        ctl = cfg["controls"]
        required = ["bank_min", "bank_max", "station_min", "station_max", 
                    "volume_min", "volume_max", "volume_step"]
        for key in required:
            if key not in ctl:
                errors.append(f"Missing controls.{key}")
    
    if "buttons" not in cfg:
        errors.append("Missing 'buttons' section")
    
    if "display" not in cfg:
        errors.append("Missing 'display' section")
    
    return errors


def validate_stations_config(cfg: Dict[str, Any]) -> list:
    """Validate stations configuration and return list of errors.
    
    Args:
        cfg: Stations config dictionary
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not isinstance(cfg, dict):
        return ["Stations config must be a dictionary"]
    
    if "banks" not in cfg:
        errors.append("Missing 'banks' section")
        return errors
    
    banks = cfg["banks"]
    if not isinstance(banks, dict):
        errors.append("'banks' must be a dictionary")
        return errors
    
    for bank_id, bank in banks.items():
        if not isinstance(bank, dict):
            errors.append(f"Bank {bank_id} must be a dictionary")
            continue
        
        if "stations" not in bank:
            errors.append(f"Bank {bank_id} missing 'stations'")
            continue
        
        stations = bank["stations"]
        if not isinstance(stations, dict):
            errors.append(f"Bank {bank_id}.stations must be a dictionary")
    
    return errors


def wait_for_mpd(max_retries: int = 10, delay: float = 1.0, logger: Optional[logging.Logger] = None) -> bool:
    """Wait for MPD to become ready.
    
    Args:
        max_retries: Maximum number of connection attempts
        delay: Seconds to wait between attempts
        logger: Optional logger for status messages
        
    Returns:
        True if MPD is ready, False if all retries exhausted
        
    Example:
        if not wait_for_mpd(logger=logger):
            logger.error("MPD failed to start")
            sys.exit(1)
    """
    import time
    
    for attempt in range(max_retries):
        result = sh(["mpc", "status"])
        if result.returncode == 0:
            if logger:
                logger.info(f"MPD ready (attempt {attempt + 1}/{max_retries})")
            return True
        
        if logger:
            logger.warning(f"MPD not ready, retry {attempt + 1}/{max_retries}")
        time.sleep(delay)
    
    if logger:
        logger.error("MPD failed to start after all retries")
    return False
