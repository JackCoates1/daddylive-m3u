import os
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://daddylive.eu/"
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REFERER = "https://daddylive.eu/"

def get_channels():
    channels = {}
    try:
        r = requests.get("https://daddylive.eu/cache/tv/tv.json", headers=HEADERS, timeout=15)
        data = r.json()
        for date, content in data.items():
            for event_type, events in content.items():
                if isinstance(events, list):
                    for event in events:
                        for ch in event.get("channels", []) + event.get("channels2", []):
                            cid = ch.get("channel_id", "")
                            name = ch.get("channel_name", "")
                            if cid and name:
                                channels[cid] = name
        print(f"tv.json: {len(channels)} channels")
    except Exception as e:
        print(f"Error: {e}")
    return channels

def get_group(name):
    n = name.lower()
    if any(x in n for x in ["sky sports", "tnt sports", "bt sport"]):
        return "Sports UK"
    elif any(x in n for x in ["bbc", "itv", "channel 4", "channel 5"]):
        return "UK TV"
    elif any(x in n for x in ["espn", "fox sports", "nbc", "cbs", "nfl", "nba", "mlb", "nhl"]):
        return "Sports USA"
    elif any(x in n for x in ["bein", "eurosport", "dazn"]):
        return "Sports International"
    elif any(x in n for x in ["ufc", "wwe", "boxing", "fight"]):
        return "Combat Sports"
    elif any(x in n for x in ["f1", "formula", "motogp", "nascar"]):
        return "Motorsport"
    elif any(x in n for x in ["tennis", "wimbledon"]):
        return "Tennis"
    elif any(x in n for x in ["cricket"]):
        return "Cricket"
    elif any(x in n for x in ["rugby"]):
        return "Rugby"
    elif any(x in n for x in ["golf", "pga"]):
        return "Golf"
    elif any(x in n for x in ["ppv", "event ppv"]):
        return "PPV"
    else:
        return "General"

def build_m3u(channels):
    lines = ["#EXTM3U"]
    for cid, name in sorted(channels.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 9999):
        group = get_group(name)
        stream_url = f"https://daddylive.eu/embed/stream.php?id={cid}&player=1&source=tv"
        lines.append(f'#EXTINF:-1 tvg-id="{cid}" tvg-logo="" group-title="{group}",{name}')
        lines.append(f'#EXTVLCOPT:http-referrer={REFERER}')
        lines.append(f'#EXTVLCOPT:http-user-agent={UA}')
        lines.append(f'#KODIPROP:inputstream.adaptive.manifest_headers=Referer={REFERER}&User-Agent={UA}')
        lines.append(f'#KODIPROP:inputstream.adaptive.stream_headers=Referer={REFERER}&User-Agent={UA}')
        lines.append(stream_url)
    return "\n".join(lines)

def main():
    os.makedirs("output", exist_ok=True)
    print("Fetching channels...")
    channels = get_channels()
    print(f"Total: {len(channels)} channels")

    m3u = build_m3u(channels)
    with open("output/playlist.m3u8", "w") as f:
        f.write(m3u)

    with open("output/index.html", "w") as f:
        f.write(f"""<html><head><title>DaddyLive M3U</title></head>
        <body>
        <h1>DaddyLive M3U Proxy</h1>
        <p>Total channels: {len(channels)}</p>
        <p><a href="playlist.m3u8">Download Playlist</a></p>
        </body></html>""")

    print(f"Done! Written to output/playlist.m3u8")

if __name__ == "__main__":
    main()
