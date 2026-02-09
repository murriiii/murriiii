#!/usr/bin/env python3
"""LoL Match Collector - fetches match data from Riot API and stores in PostgreSQL.

Usage:
    python lol_collector.py collect     # Fetch new matches only (cronjob)
    python lol_collector.py backfill    # Fetch ALL historical matches (one-time)
    python lol_collector.py mastery     # Update mastery data
    python lol_collector.py all         # collect + mastery
"""
import os
import sys
import json
import time
import psycopg2
from dotenv import load_dotenv
import riot_api_functions as rf
import data_dragon_functions as dd


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "lol_stats"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def get_stored_match_ids(conn, puuid):
    with conn.cursor() as cur:
        cur.execute("SELECT match_id FROM lol_matches WHERE puuid = %s", (puuid,))
        return {row[0] for row in cur.fetchall()}


def store_match(conn, match_id, puuid, participant, game_duration, game_start_ts):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO lol_matches (
                match_id, puuid, champion_name, kills, deaths, assists, win,
                total_minions_killed, neutral_minions_killed, position,
                time_ccing_others, ability_uses, solo_kills, takedowns,
                penta_kills, quadra_kills, triple_kills, double_kills,
                game_duration, game_start_ts
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id) DO NOTHING
        """, (
            match_id, puuid,
            participant["championName"],
            participant["kills"],
            participant["deaths"],
            participant["assists"],
            participant["win"],
            participant.get("totalMinionsKilled", 0),
            participant.get("neutralMinionsKilled", 0),
            participant.get("individualPosition", ""),
            participant.get("timeCCingOthers", 0),
            participant.get("challenges", {}).get("abilityUses", 0),
            participant.get("challenges", {}).get("soloKills", 0),
            participant.get("challenges", {}).get("takedowns", 0),
            participant.get("pentaKills", 0),
            participant.get("quadraKills", 0),
            participant.get("tripleKills", 0),
            participant.get("doubleKills", 0),
            game_duration,
            game_start_ts,
        ))
    conn.commit()


def update_mastery(conn, puuid, api_key, region_code):
    mastery_data = rf.get_masteries(region_code, puuid, api_key)
    champ_data = dd.get_champion_data()

    # Build champion ID -> name map
    id_to_name = {}
    for champ in champ_data:
        id_to_name[int(champ_data[champ]["key"])] = champ_data[champ]["name"]

    with conn.cursor() as cur:
        for m in mastery_data[:20]:  # Top 20 masteries
            champ_name = id_to_name.get(m["championId"], f"Unknown({m['championId']})")
            cur.execute("""
                INSERT INTO lol_mastery (puuid, champion_id, champion_name, champion_points, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (puuid, champion_id) DO UPDATE SET
                    champion_name = EXCLUDED.champion_name,
                    champion_points = EXCLUDED.champion_points,
                    updated_at = NOW()
            """, (puuid, m["championId"], champ_name, m["championPoints"]))
    conn.commit()
    print(f"Updated mastery for {len(mastery_data[:20])} champions")


def update_summoner(conn, puuid, api_key, region_code, game_name, tag_line):
    rank_data = rf.get_summoner_rank(region_code, puuid, api_key)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO lol_summoner (puuid, game_name, tag_line, tier, rank, lp, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (puuid) DO UPDATE SET
                tier = EXCLUDED.tier,
                rank = EXCLUDED.rank,
                lp = EXCLUDED.lp,
                updated_at = NOW()
        """, (
            puuid, game_name, tag_line,
            rank_data.get("tier", "Unranked"),
            rank_data.get("rank", ""),
            rank_data.get("leaguePoints", 0),
        ))
    conn.commit()


def fetch_and_store_matches(conn, puuid, api_key, region_name, match_ids, stored_ids):
    """Fetch match details for IDs not in stored_ids and save to DB."""
    new_ids = [m for m in match_ids if m not in stored_ids]
    if not new_ids:
        return 0

    fetched = 0
    for match_id in new_ids:
        try:
            response = rf.get_match_data(region_name, match_id, api_key)
            for p in response["info"]["participants"]:
                if p["puuid"] == puuid:
                    store_match(
                        conn, match_id, puuid, p,
                        response["info"].get("gameDuration", 0),
                        response["info"].get("gameStartTimestamp", 0),
                    )
                    fetched += 1
                    break
            time.sleep(1.5)
        except Exception as e:
            print(f"Error fetching {match_id}: {e}")
            time.sleep(5)

    return fetched


def collect(config, api_key):
    """Fetch only new matches since last collection."""
    conn = get_db_connection()
    region_code = config["Platform Routing Region Code"]
    region_name = config["Regional Routing Name"]
    name = config["Summoner Name"]

    _id, puuid = rf.get_summoner_identifiers(region_code, name, api_key, region_name)
    stored_ids = get_stored_match_ids(conn, puuid)
    print(f"DB has {len(stored_ids)} matches stored")

    # Get latest 100 match IDs
    match_ids = rf.get_summoners_matches(region_name, puuid, api_key, 0, 100)
    fetched = fetch_and_store_matches(conn, puuid, api_key, region_name, match_ids, stored_ids)

    # Update summoner info
    game_name, tag_line = name.rsplit("#", 1) if "#" in name else (name, "EUW")
    update_summoner(conn, puuid, api_key, region_code, game_name, tag_line)

    print(f"Collect done: {fetched} new matches fetched")
    conn.close()
    return fetched


def backfill(config, api_key):
    """Fetch ALL historical matches."""
    conn = get_db_connection()
    region_code = config["Platform Routing Region Code"]
    region_name = config["Regional Routing Name"]
    name = config["Summoner Name"]

    _id, puuid = rf.get_summoner_identifiers(region_code, name, api_key, region_name)
    stored_ids = get_stored_match_ids(conn, puuid)
    print(f"DB has {len(stored_ids)} matches stored, starting backfill...")

    start = 0
    batch_size = 100
    total_fetched = 0

    while True:
        match_ids = rf.get_summoners_matches(region_name, puuid, api_key, start, batch_size)
        if not match_ids:
            break

        fetched = fetch_and_store_matches(conn, puuid, api_key, region_name, match_ids, stored_ids)
        stored_ids.update(match_ids)  # Prevent refetching within same run
        total_fetched += fetched

        print(f"  Batch {start}-{start + batch_size}: {fetched} new matches (total: {total_fetched})")

        if len(match_ids) < batch_size:
            break
        start += batch_size
        time.sleep(1)

    # Update summoner info
    game_name, tag_line = name.rsplit("#", 1) if "#" in name else (name, "EUW")
    update_summoner(conn, puuid, api_key, region_code, game_name, tag_line)

    print(f"Backfill complete: {total_fetched} matches fetched, DB now has {len(stored_ids)} total")
    conn.close()


def mastery(config, api_key):
    """Update mastery data."""
    conn = get_db_connection()
    region_code = config["Platform Routing Region Code"]
    region_name = config["Regional Routing Name"]
    name = config["Summoner Name"]

    _id, puuid = rf.get_summoner_identifiers(region_code, name, api_key, region_name)
    update_mastery(conn, puuid, api_key, region_code)
    conn.close()


def main():
    load_dotenv()
    api_key = os.getenv("API_KEY") or os.getenv("RIOT_API_KEY")
    if not api_key:
        print("ERROR: API_KEY or RIOT_API_KEY not set")
        sys.exit(1)

    config = json.load(open("../readme-lol-items/config.json"))
    command = sys.argv[1] if len(sys.argv) > 1 else "all"

    if command == "collect":
        collect(config, api_key)
    elif command == "backfill":
        backfill(config, api_key)
    elif command == "mastery":
        mastery(config, api_key)
    elif command == "all":
        collect(config, api_key)
        mastery(config, api_key)
    else:
        print(f"Unknown command: {command}")
        print("Usage: python lol_collector.py [collect|backfill|mastery|all]")
        sys.exit(1)


if __name__ == "__main__":
    main()
