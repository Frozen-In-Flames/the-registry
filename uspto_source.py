"""Live USPTO source for the-registry: patent-portfolio-apis.

The registry hash chain is the nation-side record of a filing. Live
corroboration text comes from patent-portfolio-apis (the Frozen In
Flames USPTO layer, src/ppa), whose PPUBSClient implements the full
PPUBS session flow. This module locates that package, in order:

1. an installed ppa package (import ppa.uspto),
2. the checkout named by the PATENT_PORTFOLIO_APIS_DIR environment
   variable (its src directory),
3. a sibling checkout at ../patent-portfolio-apis (its src directory).

When the package cannot be located, or its client raises, callers
fall back to the registry direct PPUBS check that shipped before this
wiring. Offline behavior is therefore unchanged: the fallback labels
network failure unavailable and never raises.
"""

import os
import sys


def _ppa_uspto_module():
    try:
        from ppa import uspto
        return uspto
    except Exception:
        pass
    candidates = []
    env = os.environ.get("PATENT_PORTFOLIO_APIS_DIR")
    if env:
        candidates.append(os.path.join(env, "src"))
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "..", "patent-portfolio-apis", "src"))
    for path in candidates:
        path = os.path.normpath(path)
        if os.path.isdir(os.path.join(path, "ppa")) and path not in sys.path:
            sys.path.insert(0, path)
            try:
                from ppa import uspto
                return uspto
            except Exception:
                continue
    return None


def available():
    """True when the patent-portfolio-apis USPTO client can be imported."""
    return _ppa_uspto_module() is not None


def fetch_patent(patent_number):
    """Fetch one patent through patent-portfolio-apis.

    Returns a normalized dict with status found, or None when the
    package is unavailable or the lookup fails, so the caller can
    fall back. Never raises.
    """
    uspto = _ppa_uspto_module()
    if uspto is None:
        return None
    try:
        client = uspto.PPUBSClient()
        try:
            doc = client.fetch_patent(str(patent_number))
        finally:
            client.close()
    except Exception:
        return None
    if not doc:
        return None
    return {
        "status": "found",
        "patent_number": str(patent_number),
        "title": doc.get("inventionTitle") or doc.get("title", ""),
        "filing_date": doc.get("filingDate") or doc.get("appFilingDate", ""),
        "publication_date": doc.get("publicationDate", ""),
        "assignee": doc.get("assigneeName") or doc.get("assignee", ""),
        "source": "patent-portfolio-apis (USPTO PPUBS)",
    }
