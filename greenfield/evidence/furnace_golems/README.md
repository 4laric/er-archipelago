# Furnace golem evidence

This is the focused local datamine for #1539. [REPORT.md](REPORT.md) summarizes
the eight encounters. The tables preserve all nine MSB placement records and
all sixteen reward rows; the map-version duplicate is counted once per entity.
These files are evidence only: no world checks, taxonomy, or client behavior
are changed by this directory.

Re-run from the repository root with Python 3.9 or newer:

```sh
python tools/datamine_furnace_golems.py --msb /path/to/witchy/mapstudio --artifacts /path/to/elden_ring_artifacts --out greenfield/evidence/furnace_golems
```

`--msb` directly contains the Witchy `*-msb-dcx` directories. `--artifacts`
contains `event/*.js`, `msg/engus/*/GoodsName*.fmg.xml`, and
`vanilla_er/vanilla_er/{NpcParam,ItemLotParam_map,ItemLotParam_enemy}.csv`.
Neither input directory is modified or copied into this repository.

Source references use `msb/` and `artifacts/` prefixes relative to these two
arguments. `manifest.json` records source hashes and scan coverage, not machine
paths. The report and manifest have a fresh UTC timestamp on each run; the TSVs
are deterministic for identical inputs.

The model selection is `c5170`, established by joining placed entities to their
tear/Visage rewards. The old `c4900` lead in `gen_boss_taxonomy.py` is contradicted
by the local scan. Taxonomy integration remains follow-up work; the existing
`UNDERIVED_CLASSES` entry has not been removed by this evidence-only change.

The tool fails before publishing results on missing entity awards, disagreeing
map-version joins, missing sibling rewards, conflicting reward names, nonempty
NPC death drops, or a changed eight-entity/sixteen-reward census. A failure needs
investigation of the inputs, rather than lowering the observed coverage floor.

Synthetic tests cover arbitrary placement filenames, duplicate map versions,
empty dummy models, both reward rows, separate death/acquisition flags, portable
source references, and refusal under `python -O`:

```sh
python -m unittest -v tools/test_datamine_furnace_golems.py
```
