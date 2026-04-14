import asyncio
import os
from playwright.async_api import async_playwright

CHANNELS = {
    "1": ("Sky Sports Main Event", "Sports UK"),
    "2": ("Sky Sports Premier League", "Sports UK"),
    "3": ("Sky Sports Football", "Sports UK"),
    "4": ("Sky Sports Cricket", "Sports UK"),
    "5": ("Sky Sports Golf", "Sports UK"),
    "6": ("Sky Sports F1", "Sports UK"),
    "7": ("Sky Sports Action", "Sports UK"),
    "8": ("Sky Sports Arena", "Sports UK"),
    "9": ("Sky Sports Mix", "Sports UK"),
    "10": ("Sky Sports News", "Sports UK"),
    "11": ("TNT Sports 1", "Sports UK"),
    "12": ("TNT Sports 2", "Sports UK"),
    "13": ("TNT Sports 3", "Sports UK"),
    "14": ("TNT Sports 4", "Sports UK"),
    "15": ("BT Sport ESPN", "Sports UK"),
    "16": ("BBC One", "UK TV"),
    "17": ("BBC Two", "UK TV"),
    "18": ("ITV", "UK TV"),
    "19": ("Channel 4", "UK TV"),
    "20": ("Channel 5", "UK TV"),
    "31": ("ESPN", "Sports USA"),
    "32": ("ESPN2", "Sports USA"),
    "33": ("Fox Sports 1", "Sports USA"),
    "34": ("Fox Sports 2", "Sports USA"),
    "41": ("beIN Sports 1", "Sports International"),
    "42": ("beIN Sports 2", "Sports International"),
    "44": ("Eurosport 1", "Sports International"),
    "45": ("Eurosport 2", "Sports International"),
    "300": ("UFC Fight Night", "Combat Sports"),
    "301": ("WWE Raw", "Combat Sports"),
    "302": ("WWE SmackDown", "Combat Sports"),
    "400": ("Formula 1", "Motorsport"),
    "401": ("MotoGP", "Motorsport"),
    "500": ("Tennis TV", "Tennis"),
    "600": ("Cricket TV", "Cricket"),
    "664": ("Sky Sports PL 2", "Sports UK"),
    "700": ("Rugby TV", "Rugby"),
}

async def get_stream_url(page, channel_id):
    m3u8_urls = []

    async def handle_request(request):
        if ".m3u8" in request.url:
            m3u8_urls.append(request.url)

    page.on("request", handle_request)

    try:
        await page.goto(
            f"https://daddylive.eu/embed/stream.php?id={channel_id}&player=1&source=tv",
            wait_until="networkidle",
            timeout=30000
        )
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"Channel {channel_id} error: {e}")

    page.remove_listener("request", handle_request)

    for url in m3u8_urls:
        if ".m3u8" in url:
            return url
    return None

async def main():
    os.makedirs("output", exist_ok=True)
    lines = ["#EXTM3U"]
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            extra_http_headers={"Referer": "https://daddylive.eu/"}
        )

        for channel_id, (name, group) in CHANNELS.items():
            print(f"Processing channel {channel_id}: {name}")
            page = await context.new_page()
            url = await get_stream_url(page, channel_id)
            await page.close()

            if url:
                print(f"  Found: {url}")
                results[channel_id] = url
            else:
                print(f"  No stream found, using embed fallback")
                url = f"https://daddylive.eu/embed/stream.php?id={channel_id}&player=1&source=tv"

            lines.append(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-logo="" group-title="{group}",{name}')
            lines.append(url)
            await asyncio.sleep(2)

        await browser.close()

    # Write M3U
    with open("output/playlist.m3u8", "w") as f:
        f.write("\n".join(lines))

    # Write summary
    with open("output/index.html", "w") as f:
        f.write(f"""
        <html>
        <body>
        <h1>DaddyLive M3U Proxy</h1>
        <p>Channels: {len(CHANNELS)}</p>
        <p>Streams found: {len(results)}</p>
        <p><a href="playlist.m3u8">Download Playlist</a></p>
        </body>
        </html>
        """)

    print(f"\nDone! {len(results)}/{len(CHANNELS)} streams found")
    print("Playlist written to output/playlist.m3u8")

if __name__ == "__main__":
    asyncio.run(main())
