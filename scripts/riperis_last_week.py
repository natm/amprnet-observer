#!/usr/bin/env python3
"""Get matching prefixes from RIPE RIS."""

import json
import logging
import radix
import requests

LOG = logging.getLogger(__name__)

COVERING_PREFIXES = ["44.0.0.0/9", "44.128.0.0/10"]


def main():
    """Main entry point."""
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)8s [%(asctime)s] %(message)s')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    LOG.info('Starting')

    rtree = radix.Radix()

    # Load a portal dump snapshot, populate a radix tree
    with open("dumps/portal/20210131.json") as json_file:
        portal_prefixes = json.load(json_file)["prefixes"]
    for portal_prefix in portal_prefixes:
        rnode = rtree.add(portal_prefix["prefix"])
        rnode.data["portal_prefix"] = portal_prefix

    origin_asn = {}

    for covering_prefix in COVERING_PREFIXES:
        url = f"https://stat.ripe.net/data/routing-history/data.json?resource={covering_prefix}&min_peers=5&starttime=2021-01-01T00:00:00"
        resp = requests.get(url)
        ris = resp.json()

        for by_origin in  ris["data"]["by_origin"]:
            origin = by_origin["origin"]
            for prefix_timeline in by_origin["prefixes"]:
                prefix = prefix_timeline["prefix"]
                exact = rtree.search_exact(prefix)
                if exact is None:
                    best = rtree.search_best(prefix)
                    # is ASN in origin cache?
                    if origin not in origin_asn.keys():
                        url = f"https://stat.ripe.net/data/as-overview/data.json?resource={origin}"
                        resp = requests.get(url)
                        origin_asn[origin] = resp.json()['data']

                    print(f"{origin},{origin_asn[origin]['holder']},{prefix},{best.prefix},{best.data['portal_prefix']['data']['description']}")


        assert resp

    LOG.info("Finished")

if __name__ == "__main__":
    main()
