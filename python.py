"""SQLite database utilities for the Pocket Porridge website."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DATABASE_PATH = Path(
	os.environ.get("POCKET_PORRIDGE_DATABASE", Path(__file__).with_name("pocket_porridge.db"))
)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	email TEXT NOT NULL UNIQUE COLLATE NOCASE,
	display_name TEXT NOT NULL,
	password_hash TEXT NOT NULL,
	created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipes (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	title TEXT NOT NULL,
	description TEXT NOT NULL DEFAULT '',
	instructions TEXT NOT NULL,
	prep_minutes INTEGER NOT NULL DEFAULT 0 CHECK (prep_minutes >= 0),
	cook_minutes INTEGER NOT NULL DEFAULT 0 CHECK (cook_minutes >= 0),
	servings INTEGER NOT NULL DEFAULT 1 CHECK (servings > 0),
	image_url TEXT,
	created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
	created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingredients (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
	recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
	ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
	quantity REAL,
	unit TEXT NOT NULL DEFAULT '',
	notes TEXT NOT NULL DEFAULT '',
	PRIMARY KEY (recipe_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS saved_recipes (
	user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
	recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
	saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (user_id, recipe_id)
);

CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_ingredient ON recipe_ingredients(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_saved_recipes_user ON saved_recipes(user_id);
"""


def connect(database_path=DATABASE_PATH):
	"""Open a database connection with foreign-key enforcement enabled."""
	path = Path(database_path)
	if str(path) != ":memory:":
		path.parent.mkdir(parents=True, exist_ok=True)
	connection = sqlite3.connect(str(path))
	connection.row_factory = sqlite3.Row
	connection.execute("PRAGMA foreign_keys = ON")
	return connection


def initialize_database(database_path=DATABASE_PATH):
	"""Create the website's tables and indexes if they do not already exist."""
	with connect(database_path) as connection:
		connection.executescript(SCHEMA)


@contextmanager
def get_db(database_path=DATABASE_PATH):
	"""Yield a connection, committing on success and rolling back on errors."""
	connection = connect(database_path)
	try:
		yield connection
		connection.commit()
	except Exception:
		connection.rollback()
		raise
	finally:
		connection.close()


def create_recipe(title, instructions, *, description="", prep_minutes=0,
				  cook_minutes=0, servings=1, image_url=None, created_by=None,
				  database_path=DATABASE_PATH):
	"""Insert a recipe and return its new ID."""
	with get_db(database_path) as connection:
		cursor = connection.execute(
			"""INSERT INTO recipes
			   (title, description, instructions, prep_minutes, cook_minutes,
				servings, image_url, created_by)
			   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
			(title, description, instructions, prep_minutes, cook_minutes,
			 servings, image_url, created_by),
		)
		return cursor.lastrowid


def list_recipes(*, search=None, limit=50, offset=0, database_path=DATABASE_PATH):
	"""Return recipes ordered newest first, optionally matching a search term."""
	if limit < 1 or offset < 0:
		raise ValueError("limit must be positive and offset cannot be negative")
	query = "SELECT * FROM recipes"
	parameters = []
	if search:
		query += " WHERE title LIKE ? OR description LIKE ?"
		term = f"%{search}%"
		parameters.extend((term, term))
	query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
	parameters.extend((limit, offset))
	with get_db(database_path) as connection:
		return connection.execute(query, parameters).fetchall()


if __name__ == "__main__":
	initialize_database()
	print(f"Pocket Porridge database ready: {DATABASE_PATH}")
