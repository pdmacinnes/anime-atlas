"""Anime Atlas data pipeline: raw Kaggle CSVs -> static atlas.json.

Steps (see specs/anime-atlas.md for the full rationale):
1. Load anime metadata, drop hentai-tagged titles.
2. Load ratings, keep only "favorites" (rating >= FAVORITE_THRESHOLD).
3. Drop anime with too few total ratings to place meaningfully.
4. Build a sparse co-occurrence matrix: how often each pair of anime
   appears in the same user's favorite set.
5. Convert co-occurrence counts to PPMI (positive pointwise mutual
   information), which down-weights pairs that only co-occur because
   both are broadly popular.
6. Reduce PPMI vectors to a dense embedding via truncated SVD.
7. Project the embedding to 2D with UMAP.
8. Export one JSON record per anime with its (x, y) position and the
   metadata the frontend needs for filtering/color-by/search.

Run: python pipeline/build_atlas.py
"""

from __future__ import annotations

import ast
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from umap import UMAP

DATA_DIR = Path(__file__).parent.parent / "data" / "archive"
OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "atlas.json"

FAVORITE_THRESHOLD = 8.0  # rating >= this counts as "favorite", matching osu!Atlas's "top plays"
MIN_TOTAL_RATINGS = 100  # anime below this are too sparse to place meaningfully
MIN_COOCCURRENCE = 5  # prune noisy/rare co-occurring pairs before PMI
SVD_DIMENSIONS = 128


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def load_anime_metadata() -> pd.DataFrame:
    log("Loading animes.csv...")
    animes = pd.read_csv(DATA_DIR / "animes.csv")
    # "year" and "score" use the literal string "?" as a missing-value
    # placeholder instead of a true empty cell -- coerce to proper NaN.
    animes["year"] = pd.to_numeric(animes["year"], errors="coerce")
    animes["score"] = pd.to_numeric(animes["score"], errors="coerce")
    animes["genres_list"] = animes["genres"].apply(
        lambda s: ast.literal_eval(s) if isinstance(s, str) else []
    )
    before = len(animes)
    animes = animes[~animes["genres_list"].apply(lambda gs: "Hentai" in gs)]
    log(f"Dropped {before - len(animes)} hentai-tagged anime, {len(animes)} remain.")
    return animes


def load_favorites(keep_anime_ids: set[int]) -> pd.DataFrame:
    log("Loading ratings.csv (this is the big one, ~2.25GB)...")
    ratings = pd.read_csv(
        DATA_DIR / "ratings.csv",
        dtype={"userID": "int32", "animeID": "int32", "rating": "float32"},
    )
    ratings = ratings[ratings["animeID"].isin(keep_anime_ids)]
    favorites = ratings[ratings["rating"] >= FAVORITE_THRESHOLD]
    log(f"{len(favorites)} favorite (rating >= {FAVORITE_THRESHOLD}) ratings kept.")
    return favorites


def build_ppmi_matrix(favorites: pd.DataFrame, anime_ids: np.ndarray) -> sparse.csr_matrix:
    """Returns a sparse (n_anime x n_anime) PPMI matrix, indexed by position
    in `anime_ids` (not raw MAL animeID)."""
    id_to_idx = {aid: i for i, aid in enumerate(anime_ids)}
    favorites = favorites.copy()
    favorites["idx"] = favorites["animeID"].map(id_to_idx)

    user_codes, users = pd.factorize(favorites["userID"])
    n_users = len(users)
    n_anime = len(anime_ids)

    log(f"Building sparse user x anime favorites matrix ({n_users} users x {n_anime} anime)...")
    user_item = sparse.csr_matrix(
        (np.ones(len(favorites), dtype=np.float32), (user_codes, favorites["idx"].to_numpy())),
        shape=(n_users, n_anime),
    )

    log("Computing co-occurrence matrix (anime x anime)...")
    cooccurrence = (user_item.T @ user_item).tocoo()

    # Drop the diagonal (an anime co-occurring with itself) and low-count pairs.
    mask = (cooccurrence.row != cooccurrence.col) & (cooccurrence.data >= MIN_COOCCURRENCE)
    rows, cols, counts = cooccurrence.row[mask], cooccurrence.col[mask], cooccurrence.data[mask]
    log(f"{len(counts)} co-occurring pairs survive the min-count-{MIN_COOCCURRENCE} prune.")

    occurrence = np.asarray(user_item.sum(axis=0)).ravel()  # how many users favorited each anime
    total_favorite_events = occurrence.sum()

    # PMI(i,j) = log( (C_ij * N) / (C_i * C_j) ), clipped at 0 (PPMI) since
    # negative PMI on already-pruned rare pairs is noise, not signal.
    pmi = np.log((counts * total_favorite_events) / (occurrence[rows] * occurrence[cols]))
    ppmi = np.clip(pmi, a_min=0, a_max=None)

    log("Building PPMI sparse matrix...")
    return sparse.csr_matrix((ppmi, (rows, cols)), shape=(n_anime, n_anime))


def main() -> None:
    animes = load_anime_metadata()

    total_counts = (
        pd.read_csv(DATA_DIR / "ratings.csv", usecols=["animeID"], dtype={"animeID": "int32"})
        ["animeID"].value_counts()
    )
    keep_ids = set(total_counts[total_counts >= MIN_TOTAL_RATINGS].index)
    animes = animes[animes["animeID"].isin(keep_ids)].reset_index(drop=True)
    animes["rating_count"] = animes["animeID"].map(total_counts).astype(int)
    log(f"{len(animes)} anime remain after the >= {MIN_TOTAL_RATINGS}-rating threshold.")

    anime_ids = animes["animeID"].to_numpy()
    favorites = load_favorites(set(anime_ids))

    ppmi = build_ppmi_matrix(favorites, anime_ids)

    log(f"Running TruncatedSVD to {SVD_DIMENSIONS} dimensions...")
    svd = TruncatedSVD(n_components=SVD_DIMENSIONS, random_state=42)
    embeddings = svd.fit_transform(ppmi)
    log(f"SVD explained variance ratio (sum): {svd.explained_variance_ratio_.sum():.3f}")

    log("Running UMAP to project to 2D (this can take a few minutes)...")
    coords = UMAP(n_components=2, random_state=42, metric="cosine").fit_transform(embeddings)

    animes["x"] = coords[:, 0]
    animes["y"] = coords[:, 1]

    log(f"Writing {OUTPUT_PATH}...")
    records = []
    for _, row in animes.iterrows():
        records.append(
            {
                "id": int(row["animeID"]),
                "title": row["title"],
                "alt_title": row["alternative_title"] if isinstance(row["alternative_title"], str) else None,
                "type": row["type"],
                "year": int(row["year"]) if pd.notna(row["year"]) else None,
                "score": float(row["score"]) if pd.notna(row["score"]) else None,
                "episodes": int(row["episodes"]) if pd.notna(row["episodes"]) else None,
                "mal_url": row["mal_url"],
                "image_url": row["image_url"],
                "genres": row["genres_list"],
                "rating_count": int(row["rating_count"]),
                "x": round(float(row["x"]), 4),
                "y": round(float(row["y"]), 4),
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)

    log(f"Done. {len(records)} anime written to {OUTPUT_PATH}.")


if __name__ == "__main__":
    main()
