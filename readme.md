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

### Performance and planned improvements

The downloader and data gen tools will likely remain written in python
The solver will be rewritten in something faster at a later date.
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

At this point in time, I'm not looking for outside contributors, but please open an issue if you'd like to contribute.