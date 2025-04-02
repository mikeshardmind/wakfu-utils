#!/usr/bin/bash

pushd scripts || exit
python downloader.py
python compressed_data_gen.py
python sqlify.py
python structured_compressed_gen.py
popd || exit
pushd wakautosolver/data/ || exit
python -m apsw -nocolour items.db .dump | sed '/^\s*--/ d' > items.sql
popd || exit