#!/usr/bin/bash

cd scripts || exit
python downloader.py
python compressed_data_gen.py
python sqlify.py
python structured_compressed_gen.py
cd .. || exit
cd wakautosolver/data/ || exit
python -m apsw -nocolour items.db .dump | sed '/^\s*--/ d' > items.sql
cd ../../ || exit
