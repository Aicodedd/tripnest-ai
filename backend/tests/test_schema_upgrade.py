"""Existing local SQLite databases gain new nullable columns without losing data (STORY-018)."""
import sqlite3

from sqlalchemy import inspect

from app.db import add_missing_columns, make_engine


def test_missing_nullable_columns_are_added_and_rows_survive(tmp_path):
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.executescript("""CREATE TABLE states (id INTEGER PRIMARY KEY, code VARCHAR(4), name VARCHAR(80), kind VARCHAR(10), region VARCHAR(20));
        CREATE TABLE destinations (id INTEGER PRIMARY KEY, slug VARCHAR(80) NOT NULL, name VARCHAR(120) NOT NULL, state_id INTEGER NOT NULL,
            lat FLOAT NOT NULL, lon FLOAT NOT NULL, categories JSON, budget VARCHAR(10), daily_cost INTEGER, min_days INTEGER, best_months JSON,
            climate VARCHAR(20), description TEXT, how_to_reach TEXT, facilities JSON, featured BOOLEAN, popularity FLOAT, source VARCHAR(40), updated_at DATETIME);
        INSERT INTO destinations (slug, name, state_id, lat, lon) VALUES ('goa', 'Goa', 1, 15.5, 73.8);""")
    con.commit(); con.close()
    eng = make_engine(f"sqlite:///{path}")
    added = add_missing_columns(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("destinations")}
    assert {"image_url", "image_credit", "image_licence", "image_source_page", "image_title"} <= cols
    assert "destinations.image_url" in added
    with eng.connect() as c:
        assert c.exec_driver_sql("select slug, image_url from destinations").one() == ("goa", None)
    assert add_missing_columns(eng) == []  # idempotent
