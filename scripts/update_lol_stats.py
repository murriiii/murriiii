"""
Update League of Legends stats in GitHub profile README.
Uses Riot API v5 endpoints (current as of 2025+).
"""

import os
import re
import sys
import json
import urllib.request
import urllib.error
import urllib.parse

API_KEY = os.environ.get("RIOT_API_KEY", "")
GAME_NAME = "ムラット"
TAG_LINE = "2349"
PLATFORM = "euw1"          # platform for LoL endpoints
REGION = "europe"           # regional routing for account/match endpoints
README_PATH = "README.md"
DDRAGON_VERSION = "15.3.1"
DDRAGON_BASE = f"https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}"

# Load champion ID -> name mapping from Data Dragon
CHAMPION_MAP = {}


def api_get(url):
    """Make a GET request to Riot API."""
    req = urllib.request.Request(url, headers={"X-Riot-Token": API_KEY})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"API Error {e.code}: {url}")
        print(f"  {e.read().decode()}")
        sys.exit(1)


def load_champion_map():
    """Load champion ID to name mapping from Data Dragon."""
    global CHAMPION_MAP
    url = f"{DDRAGON_BASE}/data/en_US/champion.json"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    for name, info in data["data"].items():
        CHAMPION_MAP[int(info["key"])] = name


def get_account():
    """Get account PUUID via Riot ID."""
    encoded_name = urllib.parse.quote(GAME_NAME)
    url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{TAG_LINE}"
    return api_get(url)


def get_summoner(puuid):
    """Get summoner info (level, id) by PUUID."""
    url = f"https://{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return api_get(url)


def get_ranked(summoner_id):
    """Get ranked entries."""
    url = f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    return api_get(url)


def get_top_masteries(puuid, count=4):
    """Get top champion masteries."""
    url = f"https://{PLATFORM}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count={count}"
    return api_get(url)


def get_recent_matches(puuid, count=5):
    """Get recent match IDs."""
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
    return api_get(url)


def get_match(match_id):
    """Get match details."""
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    return api_get(url)


def format_mastery(points):
    """Format mastery points (e.g. 1202167 -> 1.2M)."""
    if points >= 1_000_000:
        return f"{points / 1_000_000:.1f}M"
    if points >= 1_000:
        return f"{points // 1_000}K"
    return str(points)


def rank_color(tier):
    """Get badge color for rank tier."""
    colors = {
        "IRON": "5C5C5C", "BRONZE": "CD7F32", "SILVER": "6c757d",
        "GOLD": "C89B3C", "PLATINUM": "21A0A0", "EMERALD": "50C878",
        "DIAMOND": "6F9FD8", "MASTER": "9B59B6", "GRANDMASTER": "E74C3C",
        "CHALLENGER": "F5C542",
    }
    return colors.get(tier, "6c757d")


def build_readme_section(summoner, ranked_entries, masteries, matches, puuid):
    """Build the HTML section for the README."""
    level = summoner["summonerLevel"]

    # Parse ranked info
    solo_rank = "Unranked"
    solo_badge = ""
    flex_rank = "Unranked"
    flex_badge = ""

    for entry in ranked_entries:
        tier = entry["tier"]
        rank = entry["rank"]
        lp = entry["leaguePoints"]
        wins = entry["wins"]
        losses = entry["losses"]
        total = wins + losses
        wr = round(wins / total * 100) if total > 0 else 0
        color = rank_color(tier)
        label = f"{tier.capitalize()} {rank}"
        detail = f"{lp} LP · {wr}% WR"

        if entry["queueType"] == "RANKED_SOLO_5x5":
            solo_rank = label
            solo_badge = f'<img src="https://img.shields.io/badge/Solo%2FDuo-{urllib.parse.quote(label)}-{color}?style=flat-square&logo=riotgames&logoColor=white"/><br/><sub>{detail}</sub>'
        elif entry["queueType"] == "RANKED_FLEX_SR":
            flex_rank = label
            flex_badge = f'<img src="https://img.shields.io/badge/Flex-{urllib.parse.quote(label)}-{color}?style=flat-square&logo=riotgames&logoColor=white"/><br/><sub>{detail}</sub>'

    if not solo_badge:
        solo_badge = '<img src="https://img.shields.io/badge/Solo%2FDuo-Unranked-6c757d?style=flat-square&logo=riotgames&logoColor=white"/>'
    if not flex_badge:
        flex_badge = '<img src="https://img.shields.io/badge/Flex-Unranked-6c757d?style=flat-square&logo=riotgames&logoColor=white"/>'

    # Build champion mastery cells
    champ_cells = ""
    for m in masteries:
        champ_id = m["championId"]
        champ_name = CHAMPION_MAP.get(champ_id, str(champ_id))
        points = format_mastery(m["championPoints"])
        champ_cells += f'<td align="center"><img src="{DDRAGON_BASE}/img/champion/{champ_name}.png" width="48"/><br/><b>{champ_name}</b><br/><sub>{points} Mastery</sub></td>\n'

    # Build recent matches
    match_rows = ""
    for match_data in matches:
        info = match_data["info"]
        # Find this player's participant data
        participant = None
        for p in info["participants"]:
            if p["puuid"] == puuid:
                participant = p
                break
        if not participant:
            continue

        champ = participant["championName"]
        kills = participant["kills"]
        deaths = participant["deaths"]
        assists = participant["assists"]
        win = participant["win"]
        kda_val = (kills + assists) / max(deaths, 1)
        result_badge = "Win-27AE60" if win else "Loss-E74C3C"
        result_text = "Win" if win else "Loss"

        match_rows += f"""<tr>
<td align="center"><img src="{DDRAGON_BASE}/img/champion/{champ}.png" width="32"/></td>
<td align="center"><b>{champ}</b></td>
<td align="center">{kills}/{deaths}/{assists}</td>
<td align="center">{kda_val:.1f} KDA</td>
<td align="center"><img src="https://img.shields.io/badge/{result_text}-{result_badge}?style=flat-square"/></td>
</tr>
"""

    section = f"""#### `> after hours`

<table align="center">
<tr>
<td align="center"><b>{GAME_NAME}#{TAG_LINE}</b><br/>Level {level} · EUW<br/><br/>{solo_badge}<br/>{flex_badge}</td>
{champ_cells}</tr>
</table>

<details>
<summary align="center"><b>Recent Matches</b></summary>
<br/>
<table align="center">
<tr><th></th><th>Champion</th><th>K/D/A</th><th>KDA</th><th>Result</th></tr>
{match_rows}</table>
</details>"""

    return section


def update_readme(section):
    """Replace the after hours section in README."""
    with open(README_PATH, "r") as f:
        content = f.read()

    # Match from "#### `> after hours`" to the next "---" or end of file
    pattern = r"#### `> after hours`.*?(?=\n---|\Z)"
    new_content = re.sub(pattern, section, content, flags=re.DOTALL)

    with open(README_PATH, "w") as f:
        f.write(new_content)

    print("README updated successfully!")


def main():
    if not API_KEY:
        print("Error: RIOT_API_KEY environment variable not set")
        sys.exit(1)

    print("Loading champion data...")
    load_champion_map()

    print("Fetching account...")
    account = get_account()
    puuid = account["puuid"]

    print("Fetching summoner info...")
    summoner = get_summoner(puuid)

    print("Fetching ranked data...")
    ranked = get_ranked(summoner["id"])

    print("Fetching top masteries...")
    masteries = get_top_masteries(puuid, count=4)

    print("Fetching recent matches...")
    match_ids = get_recent_matches(puuid, count=5)

    print(f"Fetching {len(match_ids)} match details...")
    matches = [get_match(mid) for mid in match_ids]

    print("Building README section...")
    section = build_readme_section(summoner, ranked, masteries, matches, puuid)

    print("Updating README...")
    update_readme(section)


if __name__ == "__main__":
    main()
