-- get the earliest ALS bracket for which a stat is available on each slot.
WITH part AS
  (SELECT en,
          position,
          item_lv,
          RANK() OVER(PARTITION BY position
                      ORDER BY floor((item_lv - 6) / 15) ASC) AS r
   FROM items
   NATURAL JOIN item_names
   NATURAL JOIN item_types
   WHERE RANGE > 0 -- The actual interesting condition
     AND item_lv > 0  -- excludes makabra items
     AND item_rarity not in (5,7))  -- excludes relics and epics
SELECT en,
       position,
       min(item_lv),  -- consolidate rarites, but show the range
       max(item_lv)
FROM part
WHERE r=1
GROUP BY en
ORDER BY item_lv,
         position ASC;


-- get the level where a combination of ap, mp, wp, and ra is on a non relic/epic,
-- no penalties to ap, mp, wp, or ra, and at least 1 of them is positive
WITH part AS
  (SELECT en,
          position,
          item_lv,
          ap,
          mp,
          wp,
          ra,
          RANK() OVER(PARTITION BY position, ap, mp, wp, ra
                      ORDER BY floor((item_lv - 6) / 15) * 15 + 20, item_id ASC) AS r
   FROM items
   NATURAL JOIN item_names
   NATURAL JOIN item_types
     WHERE item_lv > 0
     AND NOT (ap = 0 AND mp = 0 AND wp = 0 AND ra = 0)
     AND (ap >= 0 AND mp >= 0 AND wp >= 0 AND ra >= 0)
     AND item_rarity not in (5,7))  -- excludes relics and epics
SELECT en as [Item name (en)],
       ap,
       mp,
       wp,
       ra as ra,
       position,
       floor((min(item_lv) - 6) / 15) * 15 + 20 as [first ALS bracket combo available]
FROM part
WHERE r=1
GROUP BY en
ORDER BY item_lv,
         position ASC;


WITH part AS
  (SELECT en,
          position,
          item_lv,
          ap,
          mp,
          wp,
          ra,
          RANK() OVER(PARTITION BY position, ap
                      ORDER BY floor((item_lv - 6) / 15) * 15 + 20, item_id ASC) AS r
   FROM items
   NATURAL JOIN item_names
   NATURAL JOIN item_types
     WHERE item_lv > 0
     AND ap > 0
     AND item_rarity not in (5,7))  -- excludes relics and epics
SELECT en as [Item name (en)],
       ap,
       position,
       floor((min(item_lv) - 6) / 15) * 15 + 20 as [first ALS bracket ap avail]
FROM part
WHERE r=1
GROUP BY en
ORDER BY item_lv,
         position ASC;


WITH part AS
  (SELECT en,
          position,
          item_lv,
          ap,
          mp,
          wp,
          ra,
          RANK() OVER(PARTITION BY position, mp
                      ORDER BY floor((item_lv - 6) / 15) * 15 + 20, item_id ASC) AS r
   FROM items
   NATURAL JOIN item_names
   NATURAL JOIN item_types
     WHERE item_lv > 0
     AND mp > 0
     AND item_rarity not in (5,7))  -- excludes relics and epics
SELECT en as [Item name (en)],
       mp,
       position,
       floor((min(item_lv) - 6) / 15) * 15 + 20 as [first ALS bracket mp avail]
FROM part
WHERE r=1
GROUP BY en
ORDER BY item_lv,
         position ASC;

WITH part AS
  (SELECT en,
          position,
          item_lv,
          ap,
          mp,
          wp,
          ra,
          RANK() OVER(PARTITION BY position, wp
                      ORDER BY floor((item_lv - 6) / 15) * 15 + 20, item_id ASC) AS r
   FROM items
   NATURAL JOIN item_names
   NATURAL JOIN item_types
     WHERE item_lv > 0
     AND wp > 0
     AND item_rarity not in (5,7))  -- excludes relics and epics
SELECT en as [Item name (en)],
       wp,
       position,
       floor((min(item_lv) - 6) / 15) * 15 + 20 as [first ALS bracket wp avail]
FROM part
WHERE r=1
GROUP BY en
ORDER BY item_lv,
         position ASC;