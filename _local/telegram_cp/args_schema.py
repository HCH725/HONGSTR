import json
import shlex
from typing import Any, Dict


class ArgsValidationError(ValueError):
    def __init__(self, message: str, *, details: Dict[str, Any] = None):
        super().__init__(message)
        self.details = details or {}


def parse_args(rest: str):
    rest = (rest or "").strip()
    if not rest:
        return {}
    if rest.startswith("{") and rest.endswith("}"):
        try:
            data = json.loads(rest)
        except Exception as exc:
            raise ArgsValidationError(f"invalid json payload: {exc}") from exc
        if not isinstance(data, dict):
            raise ArgsValidationError("json payload must be an object")
        return data
    # key=value pairs
    out = {}
    try:
        parts = shlex.split(rest)
    except ValueError as exc:
        raise ArgsValidationError(f"bad args: {exc}") from exc
    for p in parts:
        if "=" not in p:
            raise ArgsValidationError(f"bad token: {p}")
        k, v = p.split("=", 1)
        key = k.strip()
        if not key:
            raise ArgsValidationError(f"bad token: {p}")
        out[key] = v.strip()
    return out


def coerce(val, typ):
    if typ == "string":
        return str(val)
    if typ == "int":
        return int(val)
    if typ == "float":
        return float(val)
    if typ == "bool":
        if isinstance(val, bool):
            return val
        s = str(val).lower()
        if s in ("1", "true", "yes", "y", "on"):
            return True
        if s in ("0", "false", "no", "n", "off"):
            return False
        raise ArgsValidationError(f"bad bool: {val}")
    if typ == "csv_string":
        if isinstance(val, list):
            return ",".join(map(str, val))
        return str(val)
    raise ArgsValidationError(f"unknown type: {typ}")


def validate(schema: dict, args: dict):
    allow_extra = schema.get("allow_extra", False)
    fields = schema.get("fields", [])
    field_map = {f["name"]: f for f in fields}
    allowed_keys = sorted(field_map.keys())

    if not allow_extra:
        extra = [k for k in args.keys() if k not in field_map]
        if extra:
            raise ArgsValidationError(
                f"unknown keys: {extra}",
                details={
                    "unknown_keys": extra,
                    "allowed_keys": allowed_keys,
                },
            )

    out = {}
    for f in fields:
        name = f["name"]
        required = bool(f.get("required", False))
        if name not in args:
            if required:
                raise ArgsValidationError(
                    f"missing required: {name}",
                    details={"allowed_keys": allowed_keys, "missing_required": [name]},
                )
            if "default" in f:
                out[name] = f["default"]
            continue
        v = args[name]
        try:
            v2 = coerce(v, f["type"])
        except Exception as exc:
            raise ArgsValidationError(
                f"type error for {name}: {exc}",
                details={"allowed_keys": allowed_keys, "field": name},
            ) from exc
        if "enum" in f and v2 not in f["enum"]:
            raise ArgsValidationError(
                f"{name} must be one of {f['enum']}",
                details={"allowed_keys": allowed_keys, "field": name},
            )
        if isinstance(v2, (int, float)):
            if "min" in f and v2 < f["min"]:
                raise ArgsValidationError(
                    f"{name} min {f['min']}",
                    details={"allowed_keys": allowed_keys, "field": name},
                )
            if "max" in f and v2 > f["max"]:
                raise ArgsValidationError(
                    f"{name} max {f['max']}",
                    details={"allowed_keys": allowed_keys, "field": name},
                )
        out[name] = v2
    return out
