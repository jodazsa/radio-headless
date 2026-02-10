#!/usr/bin/env python3
"""Shared utilities for radio-voice project.

This module provides common functionality used across encoder-controller,
oled-display, and radio-play scripts.
"""
import logging
import subprocess
import yaml
from mpd import MPDClient
from pathlib import Path
from typing import Dict, Any, Optional, List


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


def validate_hardware_config(cfg: Dict[str, Any], variant: str = "encoder_oled") -> list:
    """Validate hardware configuration for a specific hardware variant.

    Args:
        cfg: Hardware config dictionary
        variant: Hardware variant ("encoder_oled" or "rotary")

    Returns:
        List of error messages (empty if valid)
    """
    if variant == "encoder_oled":
        return _validate_encoder_oled_config(cfg)
    if variant == "rotary":
        return _validate_rotary_config(cfg)
    return [f"Unknown hardware variant: {variant}"]


def _validate_encoder_oled_config(cfg: Dict[str, Any]) -> List[str]:
    """Validate legacy encoder + OLED configuration."""
    errors: List[str] = []

    if not isinstance(cfg, dict):
        return ["Hardware config must be a dictionary"]

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


def _validate_rotary_config(cfg: Dict[str, Any]) -> List[str]:
    """Validate rotary-switch variant configuration."""
    errors: List[str] = []

    if not isinstance(cfg, dict):
        return ["Hardware config must be a dictionary"]

    i2c = cfg.get("i2c")
    if not isinstance(i2c, dict):
        errors.append("Missing or invalid 'i2c' section (must be a mapping)")
    else:
        addr = i2c.get("volume_i2c_address")
        if addr is None:
            errors.append("Missing i2c.volume_i2c_address")
        else:
            try:
                parse_i2c_addr(addr)
            except Exception as err:
                errors.append(f"Invalid i2c.volume_i2c_address ({addr!r}): {err}")

    switches = cfg.get("switches")
    if not isinstance(switches, dict):
        errors.append("Missing or invalid 'switches' section (must be a mapping)")
    else:
        for sw_name in ("station_switch", "bank_switch"):
            sw = switches.get(sw_name)
            if not isinstance(sw, dict):
                errors.append(f"Missing or invalid switches.{sw_name} (must be a mapping)")
                continue
            for bit in ("bit0", "bit1", "bit2", "bit3"):
                pin = sw.get(bit)
                if not isinstance(pin, int):
                    errors.append(f"switches.{sw_name}.{bit} must be an integer GPIO pin")

        for map_name in ("bank_decode_map", "station_decode_map"):
            decode_map = switches.get(map_name)
            if decode_map is None:
                continue
            if not isinstance(decode_map, dict):
                errors.append(f"switches.{map_name} must be a mapping of raw_code->decoded_digit")
                continue
            for raw_code, decoded in decode_map.items():
                if not isinstance(raw_code, int):
                    errors.append(f"switches.{map_name} key {raw_code!r} must be an integer")
                elif raw_code < 0 or raw_code > 15:
                    errors.append(f"switches.{map_name} key {raw_code!r} must be in range 0-15")

                if not isinstance(decoded, int):
                    errors.append(f"switches.{map_name}[{raw_code!r}] must be an integer")
                elif decoded < 0 or decoded > 9:
                    errors.append(f"switches.{map_name}[{raw_code!r}] must be in range 0-9")

    encoders = cfg.get("encoders")
    if not isinstance(encoders, dict):
        errors.append("Missing or invalid 'encoders' section (must be a mapping)")
    elif not isinstance(encoders.get("volume_encoder"), int):
        errors.append("encoders.volume_encoder must be an integer")

    controls = cfg.get("controls")
    if not isinstance(controls, dict):
        errors.append("Missing or invalid 'controls' section (must be a mapping)")
    else:
        required_ints = ["bank_min", "bank_max", "station_min", "station_max", "volume_min", "volume_max", "volume_step"]
        for key in required_ints:
            if not isinstance(controls.get(key), int):
                errors.append(f"controls.{key} must be an integer")

        if all(isinstance(controls.get(k), int) for k in ("bank_min", "bank_max")):
            if controls["bank_min"] > controls["bank_max"]:
                errors.append("controls.bank_min must be <= controls.bank_max")

        if all(isinstance(controls.get(k), int) for k in ("station_min", "station_max")):
            if controls["station_min"] > controls["station_max"]:
                errors.append("controls.station_min must be <= controls.station_max")

        if all(isinstance(controls.get(k), int) for k in ("volume_min", "volume_max")):
            if controls["volume_min"] > controls["volume_max"]:
                errors.append("controls.volume_min must be <= controls.volume_max")

        if isinstance(controls.get("volume_step"), int) and controls["volume_step"] <= 0:
            errors.append("controls.volume_step must be > 0")

    buttons = cfg.get("buttons")
    if not isinstance(buttons, dict):
        errors.append("Missing or invalid 'buttons' section (must be a mapping)")
    else:
        action = buttons.get("volume_button")
        allowed_actions = {"play_pause", "mute_toggle", "noop"}
        if not isinstance(action, str) or action not in allowed_actions:
            errors.append(
                "buttons.volume_button must be one of: play_pause, mute_toggle, noop"
            )

    polling = cfg.get("polling")
    if not isinstance(polling, dict):
        errors.append("Missing or invalid 'polling' section (must be a mapping)")
    else:
        poll_interval = polling.get("switch_poll_interval")
        debounce = polling.get("switch_debounce")
        stability_window = polling.get("switch_stability_window", 0.12)
        invalid_log_interval = polling.get("invalid_code_log_interval", 5.0)

        if not isinstance(poll_interval, (int, float)) or poll_interval <= 0:
            errors.append("polling.switch_poll_interval must be a number > 0")

        if not isinstance(debounce, (int, float)) or debounce < 0:
            errors.append("polling.switch_debounce must be a number >= 0")

        if not isinstance(stability_window, (int, float)) or stability_window < 0:
            errors.append("polling.switch_stability_window must be a number >= 0")

        if not isinstance(invalid_log_interval, (int, float)) or invalid_log_interval < 0:
            errors.append("polling.invalid_code_log_interval must be a number >= 0")

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
        client = MPDClient()
        client.timeout = 5
        client.idletimeout = None
        try:
            client.connect("localhost", 6600)
            client.status()
            if logger:
                logger.info(f"MPD ready (attempt {attempt + 1}/{max_retries})")
            return True
        except Exception:
            if logger:
                logger.warning(f"MPD not ready, retry {attempt + 1}/{max_retries}")
            time.sleep(delay)
        finally:
            try:
                client.disconnect()
            except Exception:
                pass

    if logger:
        logger.error("MPD failed to start after all retries")
    return False
