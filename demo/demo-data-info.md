# Demo data

Demo datasets are available on Zenodo repository (https://zenodo.org/records/15476933).
After downloading all the data, place it in the `demo` folder according to the following structure:

demo
|-- 2021-02
|---- input
|-------- coast *#coastline to create transects*
|-------- crop *#mask where transects will be created*
|-------- dem *#geotif file with dem*
|-------- transects *#if you have your own SHP file with transects*
|-- 2022-02
|---- input
[...]


There are config.json files on GitHub in 3 example folders that show the correct settings for each script. 
These files are not required to work and can be removed from the structure - they were developed as an help for basic configuration.