#!/usr/bin/env python3
"""Get matching prefixes from RIPE RIS."""

import json
import logging
import radix
import requests
import socket
import sys

LOG = logging.getLogger(__name__)

COVERING_PREFIXES = ["44.0.0.0/9", "44.128.0.0/10"]


class AMPRWhoisResponse(object):

    def __init__(self, raw_response):
        self._raw_response = raw_response
        self.description = ""
        self.allocated = False
        self.bgp = False
        allocated = self._find_field("Allocated:", None)
        if allocated is not None:
            self.allocated = True
            self.network = self._find_field("Network:", "")
            self.type = self._find_field("Type:", "")
            self.bgp = self._find_field("BGP:", "")
            self.description = self._find_field("Description:", "")

    def _find_field(self, fieldname, default):
        for line in self._raw_response.split("\n"):
            if line.startswith(fieldname):
                return line.split(fieldname)[1].strip()
        return default


class AMPRWhois(object):

    def __init__(self):
        pass

    def query(self, prefix):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("whois.ampr.org", 43))
        query = prefix.split("/")[0]
        # convert string to bytes, socket need bytes
        s.send((query + "\r\n").encode())

        # declares a bytes
        response = b""
        while True:
            data = s.recv(4096)
            response += data
            if not data:
                break
        s.close()

        # convert bytes to string
        content = response.decode()
        awr = AMPRWhoisResponse(raw_response=content)
        return awr


def main():
    """Main entry point."""
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)8s [%(asctime)s] %(message)s')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    LOG.info('Starting')

    whois = AMPRWhois()

    rtree = radix.Radix()

    # Load a portal dump snapshot, populate a radix tree
    with open("/home/nat/github/natm/amprnet-observer/dumps/portal/20210131.json") as json_file:
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

                    whois_entry = whois.query(prefix=prefix)

                    print(f"{origin},{origin_asn[origin]['holder']},{prefix},{best.prefix},{best.data['portal_prefix']['data']['description']},{whois_entry.allocated},{whois_entry.network},{whois_entry.type},{whois_entry.bgp},{whois_entry.description}")


        assert resp

    LOG.info("Finished")

if __name__ == "__main__":
    main()
