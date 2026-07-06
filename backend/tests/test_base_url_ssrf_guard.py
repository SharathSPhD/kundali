"""SSRF guard for user-supplied BYOK base_url values.

DNS resolution is monkeypatched throughout rather than relying on live
network access, so these tests are hermetic and deterministic in any CI
sandbox regardless of outbound network policy.
"""
import socket as socket_module

import pytest

from app.interpretation import base as base_module
from app.interpretation.base import UnsafeBaseUrlError, assert_safe_user_base_url


def _fake_resolver(mapping: dict[str, str]):
    def _getaddrinfo(host, *_a, **_kw):
        if host not in mapping:
            raise socket_module.gaierror(-2, "Name or service not known")
        return [(socket_module.AF_INET, socket_module.SOCK_STREAM, 6, "", (mapping[host], 0))]
    return _getaddrinfo


def test_public_https_host_is_allowed(monkeypatch):
    monkeypatch.setattr(
        base_module.socket, "getaddrinfo", _fake_resolver({"api.example.com": "93.184.216.34"})
    )
    assert_safe_user_base_url("https://api.example.com/v1")  # must not raise


def test_loopback_hostname_is_rejected(monkeypatch):
    monkeypatch.setattr(
        base_module.socket, "getaddrinfo", _fake_resolver({"localhost": "127.0.0.1"})
    )
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("http://localhost:11434")


def test_loopback_ip_is_rejected():
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("http://127.0.0.1:11434")


def test_ipv6_loopback_is_rejected():
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("http://[::1]:11434")


def test_cloud_metadata_ip_is_rejected():
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("http://169.254.169.254/latest/meta-data/")


def test_private_rfc1918_ip_is_rejected():
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("http://10.0.0.5:8080")
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("http://192.168.1.5:8080")
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("http://172.16.0.5:8080")


def test_non_http_scheme_is_rejected():
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("file:///etc/passwd")
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("ftp://example.com/")


def test_unresolvable_host_is_rejected(monkeypatch):
    monkeypatch.setattr(base_module.socket, "getaddrinfo", _fake_resolver({}))
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("http://this-host-does-not-exist.invalid/")


def test_hostname_resolving_to_a_private_ip_is_rejected(monkeypatch):
    """A public-looking hostname can still be DNS-rebound to a private
    address (DNS rebinding) — the resolved IP is what matters, not the
    hostname string."""
    monkeypatch.setattr(
        base_module.socket, "getaddrinfo",
        _fake_resolver({"sneaky.example.com": "169.254.169.254"}),
    )
    with pytest.raises(UnsafeBaseUrlError):
        assert_safe_user_base_url("http://sneaky.example.com/")
