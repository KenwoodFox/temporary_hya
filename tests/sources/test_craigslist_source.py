from datetime import datetime, timedelta

from notifier_bot.sources.craigslist import CraigslistSearchParams, CraigslistSource
from notifier_bot.util.craigslist import get_areas


async def test_craigslist_source_get_listings__returns_a_listing() -> None:
    area = get_areas()["New England/New York"]
    craigslist_source = CraigslistSource(
        CraigslistSearchParams(
            area=area,
            category="sss",  # general for sale
            home_lat_long=(42.36052144409481, -71.05801368957714),
        )
    )
    listings = await craigslist_source.get_listings(datetime.now() - timedelta(days=1000), limit=1)
    assert len(listings) == 1
