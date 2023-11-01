# WIP utils, published for others.


### scripts (for devs)

downloader.py: **run this first** downloads the latest supported item data from ankama's cdn

compressed_data_gen.py: generates a small bz2 compressed file for minimal redistribution if you only care about stats

sqlify.py: generates an sqlite db from downloaded item data for use in either application or manual querying.

object_parsing.py: some rough handling of objects.

solver.py: a work in progress mastery optimizing constraint based set solver.

### How to use the autosolver provided

I'm working with [wakforge.org](https://github.com/Tmktahu/wakforge)
to incorporate the autosolver's logic into their builder.

Note: Not all of the features of the autobuilder are currently available
in wakforge, and there may also be a standalone GUI app in the future.

If you'd like to make use of more of the advanced features prior to them
being included in wakforge, you'll need a little bit of knowledge on using
CLI applications, and you'll want to run solver.py after running both
downloader.py and compressed_data_gen.py

### Known limitations

- Many items are intentionally excluded at this point in time due to not handling the item conditions
  These are not in the data ankama provides, and need to be manually collected.
  I have a collection of these for items pre 215 cap expansion,
  at a later date I'll be expanding this to cover all current items then implement logic around them
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
- Weighting res based on enchanemtent system (l.ong term goal)


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


### Disclaimer

WAKFU is an MMORPG published by Ankama. The tools here are not published by or affiliated with Ankama.