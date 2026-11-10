"""G416 (docs/NINJATRADER_V38.md): the funded account (U48) sized by how the bot's previous session closed: after a
green session x after_green_mult, after a red one x after_red_mult (at least 1 contract). G372's 12-month measure (G386's
runner, its job and table), development index 2011-18 starts, unseen index 2019-25 + NQ 2015-24.

    python research/g416_after_day.py <data dir> <MNQ 09-26> <MNQ 12-26> <U48 JS json>
"""
import g386_funded_chop_pause as R

R.VARIANTS.clear()
R.VARIANTS["U48"] = {}
for g, r in ((1.5, 1.0), (1.25, 1.0), (1.0, 1.5), (1.0, 1.25), (1.0, 0.5), (0.5, 1.0)):
    R.VARIANTS[f"after green x{g}, after red x{r}"] = {"after_green_mult": g, "after_red_mult": r}

if __name__ == "__main__":
    R.main()
