import asyncio
import os
import re

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

async def get_stream_url(context, channel_id):
    captured = []

    page = await context.new_page()

    # Intercept ALL requests
    async def handle_request(request):
        url = request.url
        if any(x in url for x in [".m3u8", ".ts", "stream", "live", "hls", "playlist"]):
            captured.append(url)
            print(f"  Captured: {url}")

    async def handle_response(response):
        url = response.url
        if any(x in url for x in [".m3u8", "stream", "live", "hls"]):
            captured.append(url)
            try:
                body = await response.text()
                if "#EXTM3U" in body or "#EXT-X" in body:
                    print(f"  M3U8 response from: {url}")
                    captured.insert(0, url)
            except:
                pass

    page.on("request", handle_request)
    page.on("response", handle_response)

    try:
        # First visit the main site to get cookies
        await page.goto("https://daddylive.eu/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)

        # Now visit the embed with proper referer
        await page.goto(
            f"https://daddylive.eu/embed/stream.php?id={channel_id}&player=1&source=tv",
            wait_until="networkidle",
            timeout=30000
        )
        await page.wait_for_timeout(8000)

        # Try to get page source and find stream URLs
        content = await page.content()
        found = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', content)
        captured.extend(found)

        # Also check for iframe sources
        iframes = await page.query_selector_all("iframe")
        for iframe in iframes:
            src = await iframe.get_attribute("src")
            if src:
                print(f"  iframe src: {src}")
                captured.append(src)

    except Exception as e:
        print(f"  Error: {e}")

    await page.close()

    # Return first m3u8 URL found
    for url in captured:
        if ".m3u8" in url:
            return url

    # Return any stream URL found
    if captured:
        print(f"  Non-m3u8 URLs found: {captured[:3]}")
        return captured[0]

    return None

async def main():
    from playwright.async_api import async_playwright

    os.makedirs("output", exist_ok=True)
    lines = ["#EXTM3U"]
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={
                "Referer": "https://daddylive.eu/",
                "Origin": "https://daddylive.eu"
            },
            ignore_https_errors=True
        )

        # Set cookies to appear as a real browser
        await context.add_cookies([{
            "name": "visited",
            "value": "1",
            "domain": "daddylive.eu",
            "path": "/"
        }])

        for channel_id, (name, group) in CHANNELS.items():
            print(f"\nProcessing channel {channel_id}: {name}")
            url = await get_stream_url(context, channel_id)

            if url:
                print(f"  SUCCESS: {url}")
                results[channel_id] = url
                stream_url = url
            else:
                print(f"  FALLBACK: using embed URL")
                stream_url = f"https://daddylive.eu/embed/stream.php?id={channel_id}&player=1&source=tv"

            lines.append(f'#EXTINF:-1 tvg-id="{channel_id}" tvg-logo="" group-title="{group}",{name}')
            lines.append(stream_url)
            await asyncio.sleep(3)

        await browser.close()

    with open("output/playlist.m3u8", "w") as f:
        f.write("\n".join(lines))

    with open("output/index.html", "w") as f:
        f.write(f"""<html><body>
        <h1>DaddyLive M3U Proxy</h1>
        <p>Channels: {len(CHANNELS)} | Streams found: {len(results)}</p>
        <p><a href="playlist.m3u8">Download Playlist</a></p>
        </body></html>""")

    print(f"\nDone! {len(results)}/{len(CHANNELS)} streams found")

if __name__ == "__main__":
    asyncio.run(main())
