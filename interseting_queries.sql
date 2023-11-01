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