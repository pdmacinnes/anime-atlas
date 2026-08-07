# Anime Atlas Spec

## Requirements & Goals

Build a public, static, interactive 2D visualization of anime similarity,
directly inspired by [osu!Atlas](https://osu-atlas.ameo.dev/). Anime that
tend to be rated highly by the *same* MyAnimeList users are placed near
each other in a 2D embedding space -- a genuine "people who liked X also
loved Y" signal, not a metadata-tag similarity. Anyone can pan/zoom the
map, filter by metadata (genre, type, score, popularity, year), color
points by different stats, and search for a specific anime to locate it.

This is a separate, public project from Media Gap Finder: it's a community
discovery tool built from an aggregate public dataset, not a personal tool
tied to one MAL account. No OAuth, no personal tokens, no live API calls at
viewing time -- everything the page needs is precomputed once and shipped
as a static file.

## Data source (live-verified 2026-08-07)

**[User Animelist Dataset](https://www.kaggle.com/datasets/ramazanturann/user-animelist-dataset)**
by Ramazan Turan (GitHub: [MRamazan/User-Animelist-Dataset](https://github.com/MRamazan/User-Animelist-Dataset)).
**License: CC BY-NC 4.0 (Attribution, NonCommercial)** -- chosen over an
older CC0 alternative (Hernan Valdivieso's 2020 dataset, frozen at July
2021) specifically for recency: this one was updated ~a year ago (2025)
and covers current titles. The NonCommercial term is a real, deliberate
tradeoff, accepted because this project is a free public tool with no
monetization -- not a constraint to forget about if that ever changes.
Attribution to the dataset/author is required and will be shown on the
page itself, not just in a README.

- `ratings.csv`: 148,170,496 ratings across 1,774,522 users and 20,237
  anime. Each user has at least 5 ratings. Rating range 0.1-10.0.
- `animes.csv`: metadata -- title, alternative_title, type, year, score
  (median), episodes, mal_url, sequel flag, image_url, genres. Only
  includes anime with 100+ reviews -- very obscure titles are excluded at
  the source, not something this pipeline controls.
- The full dataset repo also ships a pretrained BERT model and pickled/
  numpy variants of the ratings (`dataset.pkl`, `ratings.npy`,
  `ratings.dat`) for the author's own recommender project -- none of that
  is needed here, only `ratings.csv` and `animes.csv`.

**Known caveats, to state clearly in the UI, not hide:**
- Includes hentai by default (per genre tags) -- excluded via the
  `genres` column before any processing touches the data.
- Less battle-tested than some alternatives (48 upvotes vs. 520+ for
  older, smaller datasets) -- reasonably documented with its own repo and
  a working demo built from a subset of it, but not as widely vetted.
- CC BY-NC 4.0 attribution requirement -- visible attribution line/link on
  the page, not just in this repo's README.

## Pipeline (offline, run locally, not live)

1. **Acquire**: download `animes.csv` and `ratings.csv` from Kaggle (manual
   download via browser, or the Kaggle CLI/API if credentials are set up
   -- the pretrained BERT model and pickle/npy variants are not needed and
   should be skipped to avoid pulling the full 7.33 GB).
2. **Clean**: drop hentai-tagged rows from `animes.csv`; drop ratings for
   those anime_ids from `ratings.csv`; drop anime below a minimum
   rating-count threshold (exact threshold TBD during implementation --
   goal is cutting obscure/noisy titles with too few ratings to place
   meaningfully, without cutting so aggressively that niche genres vanish).
3. **Embed**: treat each user's set of highly-rated anime (e.g. rating >=
   8) as an unordered "sentence" of anime IDs, and train item embeddings
   via skip-gram (gensim `Word2Vec`, `sg=1`) over these sentences -- anime
   that co-occur in the same users' favorite sets end up with similar
   vectors. This is the direct anime-domain equivalent of what osu!Atlas's
   "How it Was Built" section describes doing with tracked users' top
   plays.
4. **Project to 2D**: run UMAP over the resulting item vectors to get an
   (x, y) position per anime, preserving both local neighborhoods (so
   near-duplicates/sequels cluster tightly) and coarser genre-level
   structure (so e.g. isekai and slice-of-life form distinguishable
   regions).
5. **Export**: one static JSON file with one record per anime: `id`
   (MAL_ID), `name`, `x`, `y`, `genres`, `type`, `score`, `members`,
   `popularity`, `studio`, `year`. Designed so the frontend can filter/
   color/search with zero further computation -- no backend, ever.

## Frontend

- Plain Canvas 2D rendering of the point cloud (not WebGL -- ~15-16K
  points after cleaning is comfortably renderable on a 2D canvas; revisit
  only if real performance testing says otherwise).
- Sidebar controls modeled directly on osu!Atlas: a "Color by" dropdown
  (score / popularity / type / a highlighted genre), range filters (year,
  score, popularity/members), genre and type filters, and a search box
  that highlights and centers on a specific anime.
- Click a point for a detail panel: title, genres, studio, score, a link
  to its MAL page.
- **Dark theme** -- a deliberate style choice specific to this tool
  (unlike Media Gap Finder's old-school light/bordered-table look): a
  point-cloud visualization needs a dark background for colored points to
  read clearly, matching the reference site's own aesthetic.
- A visible, permanent note on the page itself stating the data's ~2021
  cutoff and linking the CC0 source dataset for attribution.

## Hosting

New public GitHub repo (separate from `media-gap-finder`, per the user's
choice), GitHub Pages serving a static site. Public is fine here --
unlike Media Gap Finder, this data is aggregate/community data, not tied
to any one person's account.

## Edge Cases & Error Handling

- **Anime with very few ratings**: excluded pre-embedding via the minimum-
  rating-count threshold (see Pipeline step 2), rather than placed
  unstably in the 2D map.
- **Anime absent from the dataset entirely** (too new, or under the
  source's 100-review inclusion threshold): simply not included in v1 --
  no attempt to backfill from live MAL/AniList calls, since that would
  reintroduce a live-data dependency this project is explicitly avoiding.
- **Missing/null metadata fields** in the source CSV (e.g. null
  `alternative_title`): kept as their own explicit filter bucket rather
  than causing filter logic to error or silently drop those anime.
- **Embedding/UMAP runtime**: this is a one-time offline build step, not a
  per-visitor cost -- runtime is a development-time concern only, and will
  be documented once measured, not optimized preemptively.

## Acceptance Criteria

- [ ] New public GitHub repo exists, distinct from `media-gap-finder`.
- [ ] Pipeline downloads/cleans the dataset, excludes hentai-tagged
      titles, and produces a reproducible static export file from a single
      documented command/script.
- [ ] The 2D layout visibly clusters known-similar anime on manual
      spot-check (e.g. Fullmetal Alchemist and Fullmetal Alchemist:
      Brotherhood near each other; sequels/spin-offs generally near their
      parent series).
- [ ] Frontend renders all points, supports pan/zoom, color-by, the
      documented filters, and search -- matching osu!Atlas's interaction
      model.
- [ ] The page visibly states the CC BY-NC 4.0 attribution (dataset name
      and author) and the data's collection date, not buried in a README
      only.
- [ ] Hosted and publicly reachable via GitHub Pages.
