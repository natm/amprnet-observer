#!/usr/bin/env python3
"""Get all assignments from AMPRnet portal."""

import json
import logging
import radix
import requests
import queue

from bs4 import BeautifulSoup
from datetime import datetime

LOG = logging.getLogger(__name__)


class PortalScraper(object):

    def __init__(self):
        self.rtree = radix.Radix()
        self.queue = queue.Queue()
        self.scraped = []

    def start(self):
        self.queue.put("https://portal.ampr.org/networks.php")
        while self.queue.empty() == False:
            url = self.queue.get()
            if url not in self.scraped:
                self.scraped.append(url)
                self.scrape_prefixes(url=url)

    def scrape_prefixes(self, url):
        LOG.info(url)
        response = requests.get(url, allow_redirects=False)
        if response.status_code != 200:
            LOG.warning(f"%d - %s", response.status_code, url)
            return
        # html = response.text.decode("utf-8")
        soup = BeautifulSoup(response.text, "html.parser")
        table_body = soup.find('table')
        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 0:
                prefix = cols[0].text.replace(" ", "").replace("\n", "")
                description = cols[1].text
                rnode = self.rtree.add(prefix)
                has_children = False
                for contents in cols[0].contents:
                    if contents.name == "a":
                        relative_link = contents.attrs["href"]
                        full_link = f"https://portal.ampr.org/{relative_link}"
                        self.queue.put(full_link)
                        has_children = True

                rnode.data["type"] = "assignment"
                rnode.data["description"] = description
                rnode.data["children"] = has_children

def main():
    """Main entry point."""
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)8s [%(asctime)s] %(message)s')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    LOG.info('Starting')

    scraper = PortalScraper()
    scraper.start()

    # Build an object which we can persist daily
    persist = {
        "timestamp": str(datetime.now()),
        "prefixes": []
    }

    # Dump out the radix tree
    nodes = scraper.rtree.nodes()
    for rnode in nodes:
        prefix = {
            "prefix": rnode.prefix,
            "network": rnode.network,
            "masklen": rnode.prefixlen,
            "data": rnode.data
        }
        persist["prefixes"].append(prefix)

    # write it to a file
    filename = datetime.today().strftime('%Y%m%d')
    with open(f"dumps/portal/{filename}.json", 'w') as outfile:
        json.dump(persist, outfile, indent=4)

    LOG.info("Finished")

if __name__ == "__main__":
    main()
