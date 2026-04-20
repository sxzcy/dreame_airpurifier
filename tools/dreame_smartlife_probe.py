from __future__ import annotations

import argparse
import hashlib
import json
import random
from typing import Any

import requests

USER_AGENT = "Dreame_Smarthome/1.5.59 (iPhone; iOS 16.0; Scale/3.00)"
DREAME_RLC = "1c80b3787b2266776bcdc481f37d8fa42ba10a30af81a6df-1"
BASIC_AUTH = "Basic ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg="
PASSWORD_SALT = "RAylYC%fmSKp7%Tq"


def maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = value.strip()
    if not value:
        return value
    if value[0] not in "[{":
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


class DreameProbe:
    def __init__(self, username: str, password: str, region: str) -> None:
        self.username = username
        self.password = password
        self.requested_region = region.lower()
        self.region = region.lower()
        self.tenant_id = "000000"
        self.auth_token: str | None = None
        self.uid: str | None = None
        self.session = requests.Session()

    @property
    def base_url(self) -> str:
        return f"https://{self.region}.iot.dreame.tech:13267"

    def login(self) -> None:
        url = f"https://{self.requested_region}.iot.dreame.tech:13267/dreame-auth/oauth/token"
        password_hash = hashlib.md5(f"{self.password}{PASSWORD_SALT}".encode("utf-8")).hexdigest()
        response = self.session.post(
            url,
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept-Language": "en-US;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "User-Agent": USER_AGENT,
                "Dreame-Rlc": DREAME_RLC,
                "Authorization": BASIC_AUTH,
                "Tenant-Id": self.tenant_id,
            },
            data={
                "grant_type": "password",
                "scope": "all",
                "platform": "IOS",
                "type": "account",
                "username": self.username,
                "password": password_hash,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        self.auth_token = data["access_token"]
        self.uid = str(data.get("uid", ""))
        self.tenant_id = str(data.get("tenant_id", self.tenant_id))
        self.region = str(data.get("region", self.region)).lower()

    def post_json(self, url: str, payload: dict[str, Any]) -> Any:
        response = self.session.post(
            url,
            headers={
                "Accept": "*/*",
                "Accept-Language": "en-US;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "User-Agent": USER_AGENT,
                "Authorization": BASIC_AUTH,
                "Tenant-Id": self.tenant_id,
                "Content-Type": "application/json",
                "Dreame-Auth": self.auth_token or "",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def list_devices(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/dreame-user-iot/iotuserbind/device/listV2"
        data = self.post_json(url, {"page": 1, "size": 100})
        return data.get("data", {}).get("page", {}).get("records", [])

    def get_props(self, did: str, keys: list[str]) -> list[dict[str, Any]]:
        url = f"{self.base_url}/dreame-user-iot/iotstatus/props"
        data = self.post_json(url, {"did": did, "keys": ",".join(keys)})
        result = data.get("data", [])
        return result if isinstance(result, list) else []

    def send_command(self, bind_domain: str, did: str, method: str, params: Any) -> Any:
        host = bind_domain.split(".", 1)[0]
        url = f"{self.base_url}/dreame-iot-com-{host}/device/sendCommand"
        request_id = random.randint(1000, 9999)
        payload = {
            "did": did,
            "id": request_id,
            "data": {
                "did": did,
                "id": request_id,
                "method": method,
                "params": params,
            },
        }
        return self.post_json(url, payload)

    def probe(self, bind_domain: str, did: str, max_siid: int, max_piid: int, chunk: int) -> dict[str, Any]:
        pairs = [{"siid": siid, "piid": piid} for siid in range(1, max_siid + 1) for piid in range(1, max_piid + 1)]
        found: dict[str, Any] = {}
        for start in range(0, len(pairs), chunk):
            data = self.send_command(bind_domain, did, "get_properties", pairs[start : start + chunk])
            result = data.get("data", {}).get("result", []) or data.get("result", []) or []
            for item in result:
                if item.get("code") != 0:
                    continue
                key = f"{item['siid']}.{item['piid']}"
                found[key] = maybe_json(item.get("value"))
            print(f"probed {min(start + chunk, len(pairs))}/{len(pairs)}")
        return found


def suggest_mappings(props: dict[str, Any]) -> dict[str, Any]:
    sensors: dict[str, Any] = {}
    switches: dict[str, Any] = {}
    selects: dict[str, Any] = {}

    for key, value in props.items():
        label = f"prop_{key.replace('.', '_')}"
        if isinstance(value, bool):
            switches[label] = {"key": key, "name": f"Prop {key}", "on": True, "off": False}
            continue
        if isinstance(value, int) and value in (0, 1):
            switches[label] = {"key": key, "name": f"Prop {key}", "on": 1, "off": 0}
            continue
        if isinstance(value, (int, float)):
            sensors[label] = {"key": key, "name": f"Prop {key}"}
            if 5 <= value <= 45:
                sensors[label]["unit"] = "°C"
            elif 20 <= value <= 100:
                sensors[label]["unit"] = "%"
            continue
        if isinstance(value, str) and value.isdigit():
            numeric = int(value)
            sensors[label] = {"key": key, "name": f"Prop {key}"}
            if 5 <= numeric <= 45:
                sensors[label]["unit"] = "°C"
            elif 20 <= numeric <= 100:
                sensors[label]["unit"] = "%"
            continue
        if isinstance(value, str):
            sensors[label] = {"key": key, "name": f"Prop {key}"}
    return {
        "sensor_mappings": sensors,
        "switch_mappings": switches,
        "select_mappings": selects,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Dreame Smart Life device properties.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--region", default="eu")
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument("--did")
    parser.add_argument("--max-siid", type=int, default=8)
    parser.add_argument("--max-piid", type=int, default=16)
    parser.add_argument("--chunk-size", type=int, default=20)
    args = parser.parse_args()

    probe = DreameProbe(args.username, args.password, args.region)
    probe.login()
    devices = probe.list_devices()
    if not devices:
        raise SystemExit("No devices found")

    for index, device in enumerate(devices):
        print(f"[{index}] {device.get('customName') or device.get('name')} | {device.get('model')} | did={device.get('did')}")

    if args.did:
        selected = next(device for device in devices if str(device.get("did")) == args.did)
    else:
        selected = devices[args.device_index]

    print("\nSelected device:")
    print(json.dumps(selected, indent=2, ensure_ascii=False))

    props = probe.probe(
        str(selected["bindDomain"]),
        str(selected["did"]),
        args.max_siid,
        args.max_piid,
        args.chunk_size,
    )
    print("\nDiscovered properties:")
    print(json.dumps(props, indent=2, ensure_ascii=False, sort_keys=True))

    print("\nSuggested mappings:")
    print(json.dumps(suggest_mappings(props), indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
