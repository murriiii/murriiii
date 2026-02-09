import requests
import time
import urllib.parse

class RiotApiBadRequest(Exception):
    pass


REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (GitHub-Actions; +https://github.com/murriiii/murriiii)",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://developer.riotgames.com",
}


def riot_api_get(region, endpoint, params):
    api_key = params.pop("api_key", params.pop("X-Riot-Token", ""))
    headers = {**REQUEST_HEADERS, "X-Riot-Token": api_key}
    query = "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
    url = f"https://{region}.api.riotgames.com/{endpoint}"
    if query:
        url = f"{url}?{query}"
    response = requests.get(url, headers=headers, timeout=15)
    data = response.json()
    if isinstance(data, dict) and "status" in data and data["status"]["status_code"] != 200:
        message = f"Error in getting endpoint {endpoint}\nin region {region}\n" + \
                f"with status code {data['status']['status_code']}\nwith message {data['status']['message']}"
        raise RiotApiBadRequest("Riot API Functions Error:\n" + message)
    else:
        time.sleep(0.1)
        return data


def get_summoner_identifiers(region, name, api_key, region_name="europe"):
    """Get PUUID via Riot Account API v1 (current endpoint)."""
    if "#" in name:
        game_name, tag_line = name.rsplit("#", 1)
    else:
        game_name, tag_line = name, "EUW"
    encoded_name = urllib.parse.quote(game_name)
    account = riot_api_get(region_name, f"riot/account/v1/accounts/by-riot-id/{encoded_name}/{tag_line}", {"api_key": api_key})
    puuid = account["puuid"]
    return puuid, puuid


def get_summoners_matches(region, puuid, api_key, start, count):
    matches = riot_api_get(region, f"lol/match/v5/matches/by-puuid/{puuid}/ids", {"api_key": api_key, "start": start, "count": count})
    return matches


def get_match_data(region, match_id, api_key):
    match_data = riot_api_get(region, f"lol/match/v5/matches/{match_id}", {"api_key": api_key})
    return match_data


def get_summoner_rank(region, puuid, api_key):
    """Get ranked info by PUUID (current endpoint)."""
    rank_data = riot_api_get(region, f"lol/league/v4/entries/by-puuid/{puuid}", {"api_key": api_key})
    if len(rank_data) == 0:
        return {"tier": "Unranked"}
    else:
        return rank_data[0]


def get_masteries(region, puuid, api_key):
    mastery_data = riot_api_get(region, f"lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}", {"api_key": api_key})
    parsed = []
    for champ in mastery_data:
        parsed.append({"championId": champ["championId"], "championPoints": champ["championPoints"]})
    return parsed
