# Demo data

Demo datasets are available on Zenodo repository (https://zenodo.org/records/15476933).
After downloading all the data, place it in the `demo` folder according to the following structure:

📁 demo
┣ 📁 2021-02
┃ ┣ 📁 input
┃ ┃ ┣ 📁 coast 
┃ ┃ ┃ ┗  coast.SHP #coastline to create transects
┃ ┃ ┣ 📁 crop 
┃ ┃ ┃ ┗  crop.SHP #mask where transects will be created
┃ ┃ ┣ 📁 dem 
┃ ┃ ┃ ┗  crop.SHP #geotif file with dem
┃ ┗ 📁 output
┣ 📁 2022-02
[..]

There are config.json files on GitHub in 3 example folders that show the correct settings for each script. 
These files are not required to work and can be removed from the structure - they were developed as an help for basic configuration.