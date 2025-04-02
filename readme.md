# WIP utils, published for others.


### How to use the autosolver provided

I'm working with [wakforge.org](https://github.com/Tmktahu/wakforge)
to incorporate the autosolver's logic into their builder.

Note: Not all of the features of the autobuilder are currently available
in wakforge, and there may also be a standalone GUI app in the future.

### Known limitations

- Some items are not in the item data that were previously obtainable (won't fix)
- Some items are in the item data and are no longer obtainable
  (needs thought about handling, users can exclude by name currently)
- Doesn't weight higher lv items higher based on runes possible (TODO)


### Not Yet Implemented (planned)

- Full support for sublimations which have math based solutions
- Optimizing defensive stats
- User provided stat weights mode
- Better support for stat minimums (ie. optimizing fire res specifically for ALS Gerbean s8)
- ~~a nice GUI (there are too many cli flags...).~~ [wakforge.org](https://github.com/Tmktahu/wakforge)
- Floating stat points that can be allocated by the solver.
- Weighting res based on enchanemtent system (long term goal)


### Quick notes on current optimization strategy

- Current optimization strategy handles heals and damage properly, but makes a suboptimal decision around healing.
  This will be fixed soon-ish
- Current optimization strategy is inappropriate for optimizing a tank or shielder
  and does not handle armor given/recieved equipment. This may be fixed if there is demand for it.
- Optimization strategy assumes that due to the item revamp, solving just the damage formula is appropriate for damage dealers.
  This can be improved slightly due to the enchantment system putting a higher value on fire res for ranged, air res for melee (for example) due to shared stat doubling on belts and capes between res and a desired secondary.
- Optimization strategy is fine for healers, but current over-values crit on healers.
  Crit isn't good for consistent healing output. Healing consistency is more important than damage as damage will work out on average over time, if you heal more than you need to due to a crit, you can mess up beserk. Even without beserk in play, crit is still a
  damage stat, not a heal stat, as any ap left over after healing should be spent on damage.
  There will be a toggle for optimizing healing with consistency focus that
  will be on by default if you enable healing as a secondary in the future.


### Notes on marginal utility

- Res has constant-ish marginal utility.
  In theory, Gaining 50 res is a 10.5% reduction damage taken.
  Reality is that due to rounding and a res cap, there are important breakpoints. The tooling is currently blind to this.
- Mastery has decreasing marginal utility. This should be emphasized in planned future output modes that allow comparing sets.

### Performance and planned improvements

The downloader and data gen tools will likely remain written in python
The solver may be rewritten in something faster at a later date.
Any GUI may be written in whatever I want later and just call the solver on the backend.
When this is done, the data gen tools with recieve updates to write a more efficient binary format
rather than just strip and compress what ankama provides.

Speeding this up would be with the purpose of

- Placing this in a discord bot so that people can look for items without having to download and trust code
    - This could be done now with heavy ratelimiting and a worker task
- Having it be faster for those who do know enough to trust but verify and run locally.

### Contributions?

*especially* when it comes to the stuff in community_sourced_data , could use help.

Please reach out prior to contribution if you want to avoid duplicating work,
not everyone helping with this is git-savvy


### Feedback

If you have something specific to the CLI use or use of this as a library
either open an issue or hop into the High End Wakfu server
we have a dedicated channel for it: https://discord.gg/TXNKsWhhut

If your feedback relates to how this is incoorporated into wakforge,
you should join their discord: https://discord.gg/k3v2fXQWJp instead
as some issues may be wakforge specific.


### Why can't we do better than a heuristic for stat minimums? Can't we determine on a per-slot basis the required ap, mp, wp, and range at least?

Theoretically, we could. In practice, this isn't feasible

See misc/better_than_heuristic_counterexample.py for an implementation
and then note that it takes longer to run that, which only generates per slot stat possibilities
than it does to run the current solver with a heuristic model


### Install and Run

To install and run:

- Run `pip install -r dev-requirements.txt` to install the dev dependencies
```bash
pip install -r dev-requirements.txt
```
- Run `./update.bat` (windows) or `./update.sh` (linux) to download and create the item database

#Windows:
```bash
./update.bat
```

#Linux:
```bash
./update.sh
```

- Check the `wakautosolver/data` folder for the generated database file


### Versioning

Entrypoints intended for use by other code will be kept in a fashion considered non-breaking based on known use
by other projects that are actively working with me to leverage the solver code.
If you want to leverage this and need stability, reach out.

The actual package version is in the format YYYY.MM.Patch_version. This is mostly arbitrary

### Disclaimer

WAKFU is an MMORPG published by Ankama. The tools here are not published by or affiliated with Ankama.