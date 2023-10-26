# WIP utils, published for others.


### scripts (for devs)

downloader.py: **run this first** downloads the latest supported item data from ankama's cdn

compressed_data_gen.py: generates a small bz2 compressed file for minimal redistribution if you only care about stats

sqlify.py: generates an sqlite db from downloaded item data for use in either application or manual querying.

object_parsing.py: some rough handling of objects.

solver.py: a work in progress mastery optimizing constraint based set solver.

### Just want to try it now anyhow?

If you don't know what you're doing, you probably shouldn't use this yet.
you can download python and run stdlib_standalone.py if you know enough to do that.

The standalone script will not be not updated with all changes to the WIP solver.

for windows(x86_64) users, you can grab an executable from the releases tab. 

The executable was generated from stdlib_standalone using the following:
```
py -3.11 -m nuitka --onefile .\stdlib_standalone.py
```
It will be updated when that file is meaningfully
changed until a proper build system is setup to automate this.

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
- a nice GUI (there are too many cli flags...).
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
The solver will be rewritten in something faster at a later date.
Any GUI may be written in whatever I want later and just call the solver on the backend.
When this is done, the data gen tools with recieve updates to write a more efficient binary format
rather than just strip and compress what ankama provides.

The slowest solve (lv 230, no additional constraints) takes under a minute currently.
Note: additional constraints speed up the solution due to eager discarding of sets which can't meet a constraint

```
> Measure-Command { py ./stdlib_standalone.py --lv 230  }
Days              : 0
Hours             : 0
Minutes           : 0
Seconds           : 24
Milliseconds      : 662
Ticks             : 246626187
TotalDays         : 0.000285446975694444
TotalHours        : 0.00685072741666667
TotalMinutes      : 0.411043645
TotalSeconds      : 24.6626187
TotalMilliseconds : 24662.6187
```
The script only makes use of a single thread as-is (Rel. clock speed 2.7GHz), and does not use any acceleration libraries.

Speeding this up would be with the purpose of

- Placing this in a discord bot so that people can look for items without having to download and trust code
    - This could be done now with heavy ratelimiting and a worker task
- Having it be faster for those who do know enough to trust but verify and run locally.

### Contributions?

At this point in time, I'm not actively looking for outside contributors, but please open an issue if you'd like to contribute, especially if you're interested in building a standalone website which runs this in a user's browser, or help design a more intuitive front-end for this.


### Feedback

Issue or join the wakfu optimization discord: https://discord.gg/TXNKsWhhut