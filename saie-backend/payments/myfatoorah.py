"""
payments/myfatoorah.py
-------------------------------------
Robust MyFatoorah integration layer.

Features:
- Strict 5 s per-attempt timeout (connect=2 s, read=3 s)
- 2 automatic retries on transient errors (with exponential backoff)
- Graceful fallback on Render free-tier slow networking
- Optional mock mode via MYFATOORAH_MOCK=True (skips external calls)
"""

import time
import logging
import requests
from requests.exceptions import Timeout, RequestException
from django.conf import settings

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------
HEADERS = {
    "Authorization": f"Bearer {settings.MYFATOORAH_API_KEY}",
    "Content-Type": "application/json",
}

MAX_RETRIES = 2              # retry on transient network failures
CONNECT_TIMEOUT = 2
READ_TIMEOUT = 3
TOTAL_TIMEOUT = CONNECT_TIMEOUT + READ_TIMEOUT
BACKOFF_BASE = 1.5           # seconds between retries (exponential)
LOG = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------------------
class MfTemporaryError(Exception):
    """Transient network or timeout condition. Should be retried later."""
    pass


class MfFailedError(Exception):
    """Gateway responded but marked logical failure (IsSuccess=False)."""
    pass


# ------------------------------------------------------------------------------
# Core HTTP helper
# ------------------------------------------------------------------------------
def mf_post(path: str, payload: dict, max_retries: int = MAX_RETRIES):
    """
    POST to MyFatoorah with strict timeout, retries, and logging.
    Raises:
        MfTemporaryError – network/timeout/transient issue
        MfFailedError – MyFatoorah responded with IsSuccess=False
    Returns:
        dict – parsed JSON response
    """

    url = f"{settings.MYFATOORAH_API_BASE.rstrip('/')}/v2/{path.lstrip('/')}"
    LOG.info(f"[MF] POST {url} (retries={max_retries})")

    # --------------------------------------------------------------------------
    # Mock mode (for local testing / Render DEBUG)
    # --------------------------------------------------------------------------
    if getattr(settings, "MYFATOORAH_MOCK", False):
        LOG.warning("[MF] MOCK MODE ENABLED – skipping network call.")
        time.sleep(1)
        return {
            "IsSuccess": True,
            "Message": "Mock success",
            "Data": {"InvoiceStatus": "Paid", "InvoiceTransactions": []},
        }

    # --------------------------------------------------------------------------
    # Real call loop
    # --------------------------------------------------------------------------
    attempt = 0
    while attempt <= max_retries:
        attempt += 1
        start = time.time()
        try:
            LOG.debug(f"[MF] Attempt {attempt}/{max_retries + 1} → {url}")
            response = requests.post(
                url,
                json=payload,
                headers=HEADERS,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            elapsed = time.time() - start
            LOG.debug(f"[MF] Finished in {elapsed:.2f}s (status={response.status_code})")

            response.raise_for_status()
            data = response.json()

            # Check for logical failure from gateway
            if not data.get("IsSuccess", False):
                msg = data.get("Message", "MyFatoorah error")
                LOG.error(f"[MF] Gateway returned failure: {msg}")
                raise MfFailedError(msg)

            return data

        except Timeout:
            LOG.warning(f"[MF] Timeout on attempt {attempt} ({TOTAL_TIMEOUT}s cap)")
            if attempt > max_retries:
                raise MfTemporaryError("MyFatoorah request timed out")
            time.sleep(BACKOFF_BASE * attempt)

        except RequestException as e:
            LOG.warning(f"[MF] Network error on attempt {attempt}: {e}")
            if attempt > max_retries:
                raise MfTemporaryError(f"MyFatoorah network error: {e}")
            time.sleep(BACKOFF_BASE * attempt)

        except ValueError as e:
            # JSON decode failure or similar
            LOG.error(f"[MF] Invalid JSON response: {e}")
            raise MfTemporaryError(f"Malformed response from MyFatoorah: {e}")

        except MfFailedError:
            # logical failure, do not retry
            raise

        except Exception as e:
            LOG.exception(f"[MF] Unexpected error: {e}")
            if attempt > max_retries:
                raise MfTemporaryError(str(e))
            time.sleep(BACKOFF_BASE * attempt)

    raise MfTemporaryError("Max retries exceeded – MyFatoorah unreachable")


# ------------------------------------------------------------------------------
# Simple ping helper (for debugging)
# ------------------------------------------------------------------------------
def mf_ping():
    """
    Test connectivity to MyFatoorah from Render (for diagnostics).
    Returns tuple(bool reachable, float latency)
    """
    test_url = f"{settings.MYFATOORAH_API_BASE.rstrip('/')}/v2/GetPaymentStatus"
    start = time.time()
    try:
        r = requests.post(
            test_url,
            json={"Key": "TEST", "KeyType": "PaymentId"},
            headers=HEADERS,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        latency = round(time.time() - start, 2)
        LOG.info(f"[MF] Ping OK {latency}s (status={r.status_code})")
        return True, latency
    except Exception as e:
        latency = round(time.time() - start, 2)
        LOG.error(f"[MF] Ping FAIL {latency}s: {e}")
        return False, latency