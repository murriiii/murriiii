-- LoL Stats Database Schema
-- Run: psql -U postgres -c "CREATE DATABASE lol_stats;" && psql -U postgres -d lol_stats -f db_schema.sql

CREATE TABLE IF NOT EXISTS lol_matches (
    match_id        VARCHAR(30) PRIMARY KEY,
    puuid           VARCHAR(100) NOT NULL,
    champion_name   VARCHAR(30) NOT NULL,
    kills           INTEGER NOT NULL DEFAULT 0,
    deaths          INTEGER NOT NULL DEFAULT 0,
    assists         INTEGER NOT NULL DEFAULT 0,
    win             BOOLEAN NOT NULL,
    total_minions_killed  INTEGER NOT NULL DEFAULT 0,
    neutral_minions_killed INTEGER NOT NULL DEFAULT 0,
    position        VARCHAR(20),
    time_ccing_others INTEGER DEFAULT 0,
    ability_uses    INTEGER DEFAULT 0,
    solo_kills      INTEGER DEFAULT 0,
    takedowns       INTEGER DEFAULT 0,
    penta_kills     INTEGER DEFAULT 0,
    quadra_kills    INTEGER DEFAULT 0,
    triple_kills    INTEGER DEFAULT 0,
    double_kills    INTEGER DEFAULT 0,
    game_duration   INTEGER,
    game_start_ts   BIGINT,
    fetched_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_puuid ON lol_matches(puuid);
CREATE INDEX IF NOT EXISTS idx_matches_game_start ON lol_matches(game_start_ts DESC);

CREATE TABLE IF NOT EXISTS lol_mastery (
    puuid           VARCHAR(100),
    champion_id     INTEGER,
    champion_name   VARCHAR(30),
    champion_points INTEGER NOT NULL DEFAULT 0,
    updated_at      TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (puuid, champion_id)
);

CREATE TABLE IF NOT EXISTS lol_summoner (
    puuid           VARCHAR(100) PRIMARY KEY,
    game_name       VARCHAR(50),
    tag_line        VARCHAR(10),
    tier            VARCHAR(20),
    rank            VARCHAR(10),
    lp              INTEGER DEFAULT 0,
    updated_at      TIMESTAMP DEFAULT NOW()
);
