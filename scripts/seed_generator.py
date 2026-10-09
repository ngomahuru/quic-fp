import random

META_SEED = 25062026
seeds = sorted(random.Random(META_SEED).sample(range(1_000_000), 30))
with open("scripts/seeds.txt", "w") as fh:
    fh.write("\n".join(map(str, seeds)) + "\n")
print(f"Wrote 30 seeds from meta-seed {META_SEED}")
