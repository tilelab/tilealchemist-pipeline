# Choose the number of shards

The number of shards is the only setting that sizes a run: `plan`'s
`--shards` (default 1) or `_pipeline.yml`'s `shards` (default 120).
Everything else sizes itself.

On GitHub Actions, where each shard is one job:

- At most 256, GitHub's matrix limit, and each job well under its 6-hour
  limit.
- A multiple of about 20, such as 60, 120 or 240: a public repository runs
  about 20 jobs at a time, so this fills whole waves.
- Several shards per concurrent job. Hosted runners differ in speed, so
  fast runners should be able to take more shards. Each shard costs about a
  minute of setup. The default, 120, is six per concurrent job.

On one machine, build the shards one after another; each already uses every
core. More shards only help when a shard doesn't fit on the disk.

`plan` logs each shard's share. After a run: too few shards show up as
long jobs, too many as jobs that spend more time on setup than on tiles.
