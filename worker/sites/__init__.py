"""Site scraper modülleri. Her modül `scrape(categories=None) -> list[Product]` sunar."""
from . import incehesap, itopya

SCRAPERS = [itopya, incehesap]
