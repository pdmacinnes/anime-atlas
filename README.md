# Anime Atlas

**Live: https://pdmacinnes.github.io/anime-atlas/**

A visual map of anime similarity, inspired by [osu!Atlas](https://osu-atlas.ameo.dev/)
([source](https://github.com/Ameobea/osu-beatmap-atlas)).
Anime that tend to be rated highly by the *same* MyAnimeList users are
placed near each other -- a genuine "people who liked X also loved Y"
signal, not a metadata-tag similarity.

See [`specs/anime-atlas.md`](specs/anime-atlas.md) for the full design and
methodology.

## Data

Built from [User Animelist Dataset](https://www.kaggle.com/datasets/ramazanturann/user-animelist-dataset)
by Ramazan Turan (CC BY-NC 4.0). Not redistributed here -- download it
yourself into `data/archive/` to reproduce the pipeline (see `.gitignore`;
raw data is never committed).
