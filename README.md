# CMORPH - Coastal Morphology Analysis and Visualization Application 

<p align="center">
  <img src="https://c5studio.pl/cmorph/logo.png" alt="CMORHP Logo" width="300">
</p>

This application is an improved and updated version of the CCMORPH 2.0 software (https://doi.org/10.1016/j.softx.2024.101678), which has been tested and adapted to cliff and dune coasts. 
It is a comprehensive set of Python scripts with a built-in graphical interface in Streamlit for use in a web browser. The application can be used to analyse coastal dynamics based on DEMs from various sources (UAV, LiDAR, Airborne). The scripts are client-based (run locally, with terminal or GUI support).
The basic set of tools available from the GUI includes five modules:
- Generator
- Finder
- Analyzer
- Lines
- Stats
The repository also includes an additional tool in Jupyter notebook that allows visualisation and automatic comparison of output data.

## __Basic Tools__

## ```GENERATOR```

The program is used to generate elevation profiles based on a given coastal DEM file (geotiff), a specified shoreline (SHP line) and a trimming area (SHP polygon). Basic parameters such as input and output data paths or transect parameters (lengths and spacing) can be set in the config.json file. Note that for a shoreline and a trimming area, in addition to *.shp files, *.prj files should be prepared, containing information about coordinate reference systems. In the settings, you must specify the CRS to which they are converted for further calculations.

All results are stored in separate files, which are used by other modules.

What does the program do?
1. validates input data
2. creates or cleans directories for output and intermediate data
3. initializes the database
4. generates transects based on shoreline (```data/input/coast```)
5. creates buffers around transects and for each buffer creates a DEM based on the overall image (```data/input/dem```)
6. generates elevation profiles from transects and trimmed DEM models

**What's new in this version?**
1. Improved graphical representation of processes in the terminal
2. GUI support
3. Faster calculations thanks to multi-threaded CPU support  
4. Input data and Results data are visible directly in GUI 


### Basic Configuration

The default configuration of the program can be changed by editing the ```generator-py/config.json``` file or directly in GUI on the config page. Among other things, we can specify:
- directory paths for input data,
- directory paths for output data (recommended default settings),
- path to the database (recommended default settings),
- Coordinate Reference System (CRS) - compatible with input data

#### Generator Parameters

##### `Use Precalculated Transects`
- **Description**: Enables usage of pre-generated transect lines from a shapefile instead of automatic generation.
- **Input**: Checkbox (boolean).
- **Effect**: If enabled, `transects.shp` placed in input/transects folder is used and other generation parameters are ignored.
---
##### `Transect Distance (m)`
- **Description**: Defines the spacing between consecutive transects along the shoreline.
- **Input**: Positive number (e.g., `50`).
- **Effect**: Smaller values increase density of profiles and processing time.
---
##### `Transect Length (m)`
- **Description**: Total length of each transect line.
- **Input**: Positive number (e.g., `300`).
- **Effect**: Should be long enough to cover the beach and dune zone from waterline to inland. Transects are created based on line in SHP file placed in input/coast folder, where this line will be in center point. 
---
##### `Profile Resolution (m)`
- **Description**: Sampling resolution along each transect.
- **Input**: Positive number (e.g., `1`).
- **Effect**: Defines the distance between interpolated elevation points along the transect. The best results is to set value based on DEM resolution (e.g. if DEM is 0,1 m/pix correct value is 0,1). For test or speed up process and calculate with less details default value (1) is ok.    

<p align="center">
  <img src="https://c5studio.pl/cmorph/generator-config.png" alt="generator-config" width="auto">
</p>


### GUI Features and Visualization

In the GUI interface, the Generator module provides rich visualization and validation tools for generated data.

#### **Generator Results**

After processing, results from `database.gpkg` are displayed on a map with the following layers:
- `line_source` – base shoreline used for transect generation,
- `transects` – perpendicular lines created along the coast,
- `buffer` – buffer zones used for cropping DEMs,
- `profiles` – interpolated elevation profiles,
- `points` – elevation points along each transect.

You can toggle each layer independently to inspect geometry and coverage. Fullscreen mode available.

<p align="center">
  <img src="https://c5studio.pl/cmorph/generator-db.png" alt="generator-db" width="auto">
</p>


#### **CSV Table Browsing**

All generated `.csv` files for full and cropped profiles are accessible in dropdown selectors:
- Tables display all metadata,
- Useful for debugging and manual checks per transect.
- Fullscreen mode for all tables available.

<p align="center">
  <img src="https://c5studio.pl/cmorph/generator-csv.png" alt="generator-csv" width="auto">
</p>


#### **DEM Overlay**

In the `DEM visualization` section, you can:
- Select a cropped DEM (`*_crop_*.tif`) and visualize it directly on the map,
- Analyze how DEM topography aligns with transect locations,
- Verify elevation gradients and shaded relief.

These visualization tools are essential for ensuring that profile generation is spatially accurate and cover the intended coastal zone.

<p align="center">
  <img src="https://c5studio.pl/cmorph/generator-dem.png" alt="generator-dem" width="auto">
</p>


#### **Input Data Viewer**

A dedicated tab allows for previewing all files from the `input` folder directly on an interactive map. It supports:
- visual inspection of the **shoreline** (`coast.shp`) and **trimming mask** (`clip.shp`),
- quick verification of **CRS alignment** and **geometry correctness** before processing.

<p align="center">
  <img src="https://c5studio.pl/cmorph/generator-input.png" alt="generator-input" width="auto">
</p>



## ```FINDER```

The program allows you to automatically determine the base and the top of a cliff or dune on each profile by approximating the distance between shoreline and the top.

### What does the program do?
1. reads the trimmed profiles generated by generator-py (```data/output/profiles/cropped```)
2. finds the base and the top on the profiles (available three methods described in the CCMORPH 2.0 documentation but the best results are from method 2)
3. saves finder.csv results (```data/output/results```)

**What's new in this version?**
1. Improved graphical representation of processes in the terminal
2. GUI support
3. Faster calculations thanks to multi-threaded CPU support  

### Basic Configuration

The default configuration of the program can be changed by editing the ```finder-py/config.json``` file or directly in GUI on the config page. Among other things, we can specify:
- directory paths for input data,
- input Profiles Path (recommended default settings)
- directory paths for output data (recommended default settings),

#### Finder Parameters

##### `Min Profile Points` (integer)
- **Description:**: Minimum number of points required in a profile for it to be included in the analysis.
- **Purpose:**: Avoids analyzing extremely short or corrupted profiles that may lead to unreliable feature detection.
- **Default value:**: `10`  
- **Example:**: Profiles with fewer than 10 points will be skipped entirely.
---
### `Elevation Zero` (float)
- **Description:**: Reference elevation (in meters) used to define where the profile intersects with a defined "zero level", typically corresponding to the beach/shore transition.
- **Purpose:**: Used to detect: 
    - `first_zero` – the first point rising above this elevation,
    - `last_zero` – the last point below this elevation.
- **Default value:**: `0.50` (meters above sea level). This value should depend on the height of DEM, sea level and beach level.    
- **Example:**: If set to `0.50`, the finder will look for profile points where the elevation crosses that level, often delineating the width of the dry beach.  If the coastline is at level ‘0.0’, the best solution is to set this value to ‘0.1’. 
---
### `Beyond Top Buffer` (integer)
- **Description:**: Number of additional points to analyze **beyond the detected dune crest (`top`)**.
- **Purpose:**: Ensures that the algorithm checks if the detected top is indeed the true crest, or if higher elevations exist slightly farther inland. It refers to the distance between the maximum height point (top point of the cliff) to the last point determined by the algorithm. It informs how far beyond the highest point of the profile the profile itself ends (as long as we do not go beyond its maximum range).
- **Default value:**: `10`  
- **Example:**: If the dune crest is found at index `42`, the analysis will continue through index `52` (i.e., 10 more points).
---
### Summary Table

| Parameter             | Type     | Default | Description                                                  |
|-----------------------|----------|---------|--------------------------------------------------------------|
| `min_profile_points`  | integer  | `10`    | Minimum number of points to include a profile in processing. |
| `elevation_zero`      | float    | `0.50`  | Elevation threshold to detect first/last zero crossing.      |
| `beyond_top_buffer`   | integer  | `10`    | Number of points to analyze beyond the detected dune crest.  |


<p align="center">
  <img src="https://c5studio.pl/cmorph/finder.png" alt="finder" width="auto">
</p>


### GUI Features and Visualization

The GUI interface of the Finder module offers dynamic visualization and quick inspection tools to validate the detection of characteristic points along coastal profiles.

#### **Finder Results Table**

- Displays the contents of `finder.csv` generated by the script.
- Each row corresponds to a transect/profile and includes:
  - Profile ID,
  - Selected method number,
  - Optional smoothing flag (`profile_smooth`),
  - Detected values for: `first_zero`, `last_zero`, `bottom`, and `top`.
- Supports sorting and scrolling for better overview of longer datasets.
- Allows direct download of the full CSV file.

<p align="center">
  <img src="https://c5studio.pl/cmorph/finder-cs.png" alt="finder-csv" width="auto">
</p>

#### **Quick Charts for Single Profiles**

- Automatically visualizes key points (`first_zero`, `last_zero`, `bottom`, `top`) for a selected profile.
- Displays a labeled, color-coded horizontal schematic of the profile with:
  - Red: first crossing of elevation threshold (`first_zero`)
  - Blue: last crossing (`last_zero`)
  - Green: base (`bottom`)
  - Orange: top (`top`)
- Useful for reviewing detection quality profile by profile.

#### **All Profiles Overview**

- A line chart showing the variation of all four detected values across profile IDs.
- Helps identify:
  - Anomalies in top/bottom detection,
  - Profile gradients or discontinuities,
  - Consistency in shoreline threshold detection.
- Option to toggle shoreline orientation (`Water in the north` vs `Water in the south`) to match real-world geometry.

These tools allow rapid validation of Finder results, supporting both quality control and deeper insight into spatial trends in coastal morphology.

<p align="center">
  <img src="https://c5studio.pl/cmorph/finder_chart.png" alt="finder_chart" width="auto">
</p>



## ```ANALYZER```

The program collects information about the bases and tops of profiles (generated automatically or marked manually) and calculates their properties such as distance, slope and volume. 

### What does the program do?
1. reads the trimmed profiles generated by generator-py (```data/output/profiles/cropped```)
2. reads information about profiles whose base and top have already been automatically determined by finder-py (```data/output/finder/finder.csv```)
3. determines profile parameters (distance, slope, volume) for designated bases and tops
4. saves the results in a csv file (```data/output/analyser/measurement.csv```)
5. saves lists of tops and bases separately to shp files (```data/output/analyser/shapes```)

### Basic configuration
The default configuration of the program can be changed by editing the ```analyser-py/config.json``` file or directly in GUI on the config page. Among other things, we can specify:
- base paths to the input data,
- paths to the input and output data (recommended default settings),
- path to database.gpkg (recommended default settings)
- format of csv files from finder-py and for output (recommended default settings) 
- Coordinate Reference System (CRS) for output shape files

#### Additional Parameters

##### `Selected Profiles`
- **Description**: Allows specifying a subset of profile IDs for which analysis will be run.
- **Input**: Comma-separated list of integers (e.g., `1,3,5,8`).
- **Effect**: All other profiles are ignored during processing.
---
##### `Methods Order`
- **Description**: This parameter allows to define the order in which point feature detection algorithms (such as dune base and peak) are applied. For each profile, the system attempts to apply the methods in the specified order and selects the first correct result. This allows you to test different detection approaches and prioritise methods that work better for a given dataset..
- **Input**: Comma-separated indices (e.g., `0,2,1`).
- **Details**: Each number refers to a specific method:
  - `0`: Zero Crossing - The first intersection of the profile with the reference level
  - `1`: Max Curvature - Point of maximum curvature change on the profile
  - `2`: Elevation Threshold - The point at which a specified altitude value is exceeded.
- **Purpose:**: 
  - Flexibility - allows you to adapt the analysis to data of different quality; 
  - Safety of calculations - if one method fails, another can produce a result.
- **Use case**: If the first method fails, the next one in the order is tried.
---
##### `Max Error`
- **Description**: Defines the maximum allowed error (in meters) during geometric fitting of shoreline features. It is the tolerance threshold to accept or reject a particular section of the profile as a representative section of the dune/beach
- **Details**: For each method used to determine a characteristic point (e.g., peak or base detection), the model fitting error (e.g., linear regression or other simplified model to points) is calculated. If this error is less than Max Error, the result is accepted and saved to the results. If it is greater, the method is considered ineffective for the given profile.
- **Input**: Decimal number (e.g., `3.0`).
- **Effect**: Higher values make the model more tolerant to irregular shapes but can reduce precision. A lower max_error value (e.g., 1.0) means greater accuracy, but fewer accepted results.


<p align="center">
  <img src="https://c5studio.pl/cmorph/analyzer-config.png" alt="analyzer-config" width="auto">
</p>


### GUI Features and Visualization

The `Analyzer` module in the GUI presents results of morphological feature extraction from profiles in an intuitive and interactive manner. It includes two key sections: **Results** and **Map**.

---

#### **Results Tab**

This tab displays the content of the `analyzer.csv` file, which contains detailed morphological parameters for each profile:

- **Core Points** (by ID and coordinates):
  - `first_zero`, `last_zero`, `bottom`, `top`
- **Geolocation and Elevation**:
  - Coordinates and elevation for each detected point
- **Beach and Dune Characteristics**:
  - `beach_width`, `beach_volume`
  - `dune_width`, `dune_volume`
  - `beach_slope`, `dune_slope`

##### Features:
- Scrollable and sortable data table for fast inspection.
- CSV export button to download the full table.
- Provides essential morphometric data ready for statistical analysis or machine learning.


<p align="center">
  <img src="https://c5studio.pl/cmorph/analyzer-res.png" alt="analyzer-results" width="auto">
</p>


---

#### **Visualization Section**

Includes six interactive chart modules that can be toggled individually:

1. **Position and Elevation** – plots point ID vs. elevation for each profile (useful for understanding relative terrain shape).
2. **Beach Width** – profile-wise plot showing width of the beach (distance from zero to bottom).
3. **Dune Width** – profile-wise plot showing dune width (distance from bottom to top).
4. **Beach and Dune Slope** – combined line plot with slope values in degrees.
5. **Beach and Dune Volume** – bar plots for estimated volume in m³.
6. **Top and Bottom Elevation** – elevation values for top and bottom points (helps verify relative height of the dune or cliff).

These charts support rapid validation of trends and anomalies in profile geometry across the whole area.

<p align="center">
  <img src="https://c5studio.pl/cmorph/analyzer-vis.png" alt="analyzer-vis" width="auto">
</p>

---

#### **Map Tab**

A web map with overlayed detected points:

- Interactive markers showing:
  - `first_zero` (red)
  - `last_zero` (blue)
  - `bottom` (green)
  - `top` (purple)
- Hover tooltips displaying the profile ID and elevation for each point.
- Background: OpenStreetMap.

The map allows spatial validation of morphology detection, helping ensure geospatial consistency and assess terrain structure visually.

<p align="center">
  <img src="https://c5studio.pl/cmorph/analyzer-map.png" alt="analyzer-map" width="auto">
</p>



## __Additional Tools in GUI__

## ```LINES```

This tool allows you to generate continuous lines based on points calculated in the Analyzer module. It supports the creation of lines representing the bottom, top, first zero, and last zero points extracted along each elevation profile.
The generated lines are saved in `GeoJSON` format inside the `data/output/lines` folder. These files are compatible with most GIS software (such as QGIS) and are also used as the basis for the statistical calculations performed in the `STATS` module.

### GUI Features

The GUI for the `LINES` module includes the following features:

- **Path Selector**: You can define the path to the main folder containing the profile point data using a dropdown or path field. This is usually a folder containing previous analyses, but NOT individual subfolders with dates, only the parent folder, e.g., `../../demo`.
- **Layer Selection**: A checkbox interface allows you to select which layers to process. Available options include:
  - `bottomPoints` – representing the bottom of dune or cliff
  - `firstZeroPoints` – the first crossing of elevation zero from the shoreline side
  - `lastZeroPoints` – the last zero crossing of elevation zero from the shoreline side, 
  - `topPoints` – the top of the dune or cliff 
- **Line Creation**: After selecting the desired point categories, clicking the `Create line` button will run the line-generation process. Each selected point category will be converted into a smoothed and ordered line.

<p align="center">
  <img src="https://c5studio.pl/cmorph/lines.png" alt="lines" width="auto">
</p>

**Result Preview**: Generated lines are displayed on a OpenStreet map viewer directly within the GUI, overlaid on a basemap for spatial validation. Each line has a distinct color, making it easy to verify alignment and coverage along the coastal transects.

This functionality enables easy inspection and correction of the profile point outputs and ensures that the derived lines are spatially coherent before performing further analysis.

<p align="center">
  <img src="https://c5studio.pl/cmorph/lines-map.png" alt="lines-map" width="auto">
</p>



## ```STATS```

This module performs **statistical analysis of shoreline changes** based on previously detected shorelines from elevation profiles. It calculates well-established indicators used in coastal morphodynamics such as:

- **LRR (Linear Regression Rate)** – shoreline change rate based on a linear regression of all points in time.
- **EPR (End Point Rate)** – shoreline change rate based on the difference between the oldest and newest shoreline position.
- **SCE (Shoreline Change Envelope)** – the total distance between the farthest and closest shoreline positions observed.
- **NSM (Net Shoreline Movement)** – the distance between the oldest and most recent shoreline (signed, not absolute).
- **EPR & LRR Visualization** – color-coded bar representations of erosion (red) and accretion (green) per transect.

All computations are based on GeoJSON files containing multiple shoreline positions and a predefined set of transects.
No separate `config.json` is required. All settings and file selection are done through GUI using default paths. 

---

### What does the program do?

1. Loads shoreline geometries and matching transect lines.
2. For each transect, calculates the intersection points with all shorelines.
3. Computes the following metrics for each transect:
   - LRR (including R² and number of time points),
   - EPR,
   - NSM,
   - SCE.
4. Aggregates statistical summaries (min, max, average, number of erosional/accretional transects).
5. Visualizes shoreline change per transect using colored bars.
6. Exports detailed CSV tables and PNG summary graphics to the `stats/output` directory.

---

<p align="center">
  <img src="https://c5studio.pl/cmorph/stats.png" alt="stats" width="auto">
</p>



### Output Files

The following CSV files are displayed in table format and can be downloaded directly from the STATS page in the GUI:
- `LRR_results.csv` – linear regression stats per transect.
- `EPR_results.csv` – endpoint rate per transect.
- `SCE_results.csv` – shoreline change envelope per transect.
- `NSM_results.csv` – net shoreline movement per transect.

Additionally, PNG files are created for NSM, EPR, and LRR, which are saved in the data/stats/output folder.

---

### Interpretation of Indicators

#### `LRR` (Linear Regression Rate)
- **Definition**: Trend of shoreline movement based on least-squares regression through time.
- **Output**: `LRR_rate`, R², and number of years (n).
- **Use case**: Long-term trend analysis.
- **Positive** = accretion, **Negative** = erosion.

#### `EPR` (End Point Rate)
- **Definition**: Rate calculated from the first and last available shoreline positions.
- **Output**: `EPR_rate`.
- **Use case**: Simplified trend over time.
- **Positive** = accretion, **Negative** = erosion.

#### `NSM` (Net Shoreline Movement)
- **Definition**: Distance between oldest and newest shoreline (signed).
- **Use case**: Shows net movement direction without considering rate.

#### `SCE` (Shoreline Change Envelope)
- **Definition**: Distance between most landward and most seaward shoreline.
- **Use case**: Represents total shoreline variability.

<p align="center">
  <img src="https://c5studio.pl/cmorph/stats3.png" alt="stats3" width="auto">
</p>


## __Notebook Scripts__

## `FIGURES`

The `figures.ipynb` notebook is designed to automatically generate illustrations based on key features of coastal profiles (dune or cliff systems), such as zero crossing points, top (crest), and bottom (base). These figures help in visual validation and comparison of morphological changes across multiple datasets.

### Main Functionality

The notebook processes multiple `.csv` files and visualizes transect profiles, marking critical positions such as:
- **first_zero** – first zero crossing
- **last_zero** – last zero crossing
- **bottom** – lowest point (base)
- **top** – highest point (crest)

For each profile found in the CSV, a profile line is plotted and annotated with these key points.

### What does the notebook do?

1. **Loads input data**: One `.csv` files containing profile information (with columns like `profile_id`, `first_zero`, `last_zero`, `bottom`, `top`, etc.).
2. **Processes the data**: Iterates over profiles and extracts position and elevation data.
3. **Plots annotated figures**: Creates profile-wise illustrations with key points marked and labeled.
4. **Exports results**: Saves the figures as `.jpg`, `.png`, or `.svg` in the output directory.

### Available Options (via code cells)

- `zoom` – toggle zoom on detailed region of interest
- `out_format` – choose output format (JPG, PNG, SVG)
- `cut_window` – specify slicing window for visual clarity
- `multiple_files` – process multiple CSVs and generate comparative plots
- `title` – set filename suffix and figure title based on dataset

### Output

The output files are saved automatically in the format:
```
{OUTPUT_FOLDER}/{title}.cut[.zoom].{format}
```

<p align="center">
  <img src="https://c5studio.pl/cmorph/figures.png" alt="figures" width="auto">
</p>


These images can be used for:
- Visual QC of automated detection points
- Presentations or publications
- Quick comparison between different time steps or methods

---

## `FIGURES_COMPARED`

The `figures_compared` notebook allows direct visual comparison between two or more sets of profile data (e.g., from different years or time periods). It generates overlapping plots that help identify significant differences in key morphological features such as the beach and dune volume, top and bottom elevation, or shoreline position.

### What does the program do?
1. Loads selected CSV files containing calculated feature points (top, bottom, zero) and their profile-wise positions and elevations.
2. For each profile ID, creates a combined comparison figure showing both lines along the same axis.
3. Adds automatically generated annotations indicating the detected points for each key.
4. Saves the visual comparison as a static figure (`PNG`, `JPG`, or `SVG`) in the output directory.

### Output
The resulting figure includes:
- Profile lines from both selected files, clearly color-coded.
- Filled areas or arrows indicating differences in elevation or position (blue line is a last time period).
- Automatically generated labels on last line, showing exact height of points and position on transect line (X Axis).
- Annotation in legend box to each lines with name of data folder and position on transect line (zero,bottom,top). \n

- **Use case** 
The value of each point can be used to quickly calculate changes directly from the graph. All we need to know is the “Profile Resolution” parameter set in the Generator (when set to 1, it means 1 m; if the value was set to 0.1, it means that one point has a value of 0.1 m on the graph). 
So, to calculate the width of the beach for 2024-05 in the image below, simply perform the following operation: 212-195=17 m (because the point value in the generator was set to 1 m).
Similarly, you can calculate the differences between the positions of points in individual years, e.g., the position of the coastline shifted between 2021-02 and 2024-05 by 12 m (195-183=12).    

<p align="center">
  <img src="https://c5studio.pl/cmorph/figures-compare.png" alt="figures-compare" width="auto">
</p>


These plots are particularly useful for:
- Comparing storm impacts,
- Visualizing seasonal or annual changes,
- Validating changes detected by other modules (e.g., STATS or Analyzer).


---

## ```DIFFERENCES```

The `differences` notebook is designed to perform comparative analyses between dune or cliff profile datasets from two different time periods. It highlights morphological changes (e.g., in slope, width, or volume) and presents them in clear visual form. This helps to identify areas of significant transformation over time.

### What does the program do?
1. Loads selected CSV files from analyzer module containing values for individual profiles (`dune_slope`, `dune_volume`, `dune_width`, etc.) for two selected dates.
2. Computes differences in selected parameters between two time periods, such as:
- Dune slope
- Dune width
- Dune volume
- Beach slope
- Beach width
- Beach volume
3. Visualizes these differences in various formats:
   - **Change maps** with color-coded profiles and base DEM in bacground to see position of changes
   <p align="center">
      <img src="https://c5studio.pl/cmorph/diff_map.jpg" alt="diff-map" width="auto">
    </p>

   - **Line plots** showing profile-wise differences 
   <p align="center">
      <img src="https://c5studio.pl/cmorph/diff_plot.jpg" alt="diff-plot" width="auto">
    </p>

   - **Heatmaps** for overview of magnitude and direction of changes 
    <p align="center">
      <img src="https://c5studio.pl/cmorph/heatmap.jpg" alt="heatmap" width="auto">
    </p>


### Key Features
- Clear spatial context with map-based visualization (optional background imagery with shaded DEM for better interpretation).
- Profile numbers are overlaid for better correspondence to input datasets.
- Color scale reflects the magnitude and direction of change (blue for decrease, red for increase).

### Input Requirements
- Two CSV files generated by the Analyzer for different dates.
- Consistent profile structure and ID across the input files.
- Folder structure and paths defined accordingly in the script.

### Output
- PNG/JPG/SVG files saved in the designated output directory (e.g., output/figures-diff/)
- Change maps are titled with the dates and metric, e.g., 2021-02_2024-05_dune_slope_map.jpg
- Summary plots per metric saved with consistent filenames for easier automation.

These results are used for qualitative interpretation and can be included directly in reports or presentations.

---
- **Note**
For best results, make sure both CSV files contain the same number and order of profiles, and that all required fields are present. All visualizations are generated with consistent formatting and color schemes to ensure easy comparability across different morphological variables and time intervals.
---

This notebook is ideal for monitoring coastal dynamics and identifying zones of erosion or accretion over time. It supports visual validation of changes detected algorithmically in previous modules (e.g., analyzer).

---

## ```DEM_COMPARED```

The `dem_compared` notebook is designed to visually compare the spatial position of key morphological points (e.g., first zero, bottom, top) across multiple dates for each profile. It overlays these points on DEM (Digital Elevation Model) images to allow visual inspection of profile shifts and changes over time.

### What does the program do?
1. Loads raster background images (hillshade DEMs) for the selected data sets.
2. Reads point positions for multiple dates from corresponding CSV files (must include profile ID and x/y positions of features like `first_zero`, `bottom`, `top`).
3. For each profile:
   - Plots multiple DEMs side by side (one per selected date).
   - Overlays the detected key points using consistent color and symbol scheme.
   - Labels each point with the corresponding position on transect line (e.g., 183, 202, 214). This value is a parameter that can help us understand the changes on each points. You need to only know “Profile Resolution” parameter set in the Generator (when set to 1, it means 1 m; if the value 0.1, it means that one point has a value of 0.1 m on the graph)

### Key Features
- Visual representation of temporal change for each profile.
- Clear spatial context provided by the DEM background.
- All relevant features (first zero, bottom, top) plotted with profile-wise consistency.
- Compact layout: all dates are shown side by side for each profile.

### Input Requirements
- DEM images created in Generator script.
- CSV files with columns for each point’s X, Y position per profile created in Analyzer script.

### Output
- PNG image per profile with overlaid morphological points.

    <p align="center">
      <img src="https://c5studio.pl/cmorph/dem-compare.png" alt="dem-compare" width="auto">
    </p>


### Example
Each output figure shows one row of panels — one panel per date — with point IDs and markers over a grayscale hillshade, allowing direct visual comparison of point migration and morphological changes.

This notebook is especially useful for qualitative validation of automatically detected features and for generating publication-ready visual summaries of morphological change.

---

## ```CSV_COMPARED```

The script takes the generated CSV file from analyzer-py for comparison, and you can input multiple CSV files for comparison.

### What does the program do?
1. Reads the morphological properties inside the CSV from Analyzer script
2. Compares the properties between inputted CSV files
3. Saves the results of multiple CSVs in a single csv file (data/CSV/compare_data)

---

## ```CSV_COMPARED_2```

The script takes the generated CSV file from analyzer-py for comparison, the user make comparison between TWO different CSV files.

### What does the program do?
1. Reads the morphological properties inside the CSV from Analyzer script
2. Compares the properties between both CSV files.
3. Saves the results of CSVs in a single csv file  (data/CSV/compare_2_files)


---

## ```Requirements and initialisation```

Most of the tests (for both tools and auxiliary scripts) were performed on Linux Ubuntu 22.04.1 LTS using WSL2 running on Windows 11 Pro. The operation of the tools themselves was also tested on macOS Big Sur 11.7.1 and Windows 11 Pro. The Python interpreter version 3.10 was used each time, and the versions of the individual packages can be found in the requirements file.

The systems required the GDAL and Rtree tools to be installed. For Linux Ubuntu, this can be done as follows:
```
sudo apt install gdal-bin libgdal-dev python3-rtree
```

It is recommended that you use the Python Virtual Environment. This protects against version conflicts of previously installed packages. The easiest way to create and activate a virtual environment for testing is to call the following commands (Linux system) in the project root directory:

```
python3 -m venv cmorph
source cmorph/bin/activate
```

Install the necessary packages using the information in the requirements.txt file. Note that we must remember to enter the correct version of the previously installed GDAL tool in this file. So first check the version:

```
gdalinfo --version
```

then edit the requirements.txt file, modifying the GDAL version stored there to the version obtained in the previous step (e.g. GDAL==3.4.1). Finally, install the required packages:

```
pip install -r requirements.txt
```

To run app with GUI use code below:

```
streamlit run app.py
```

## ```Demo data```
Once the environment has been initialised, we can start testing the tools. Five sets of test data (same area, different periods) have been prepared to download on ZENODO repository (https://zenodo.org/records/15476933). 
All test data should be placed in the ```demo``` directory, respectively in subdirectories ```2021-02```, ```2022-02``` etc. 
Each directory contains the input data for calculations. On GitHub repository are corresponding configuration files in each folders. 


The calculation can take, depending on the computer used, quite a long time. We are kept informed of the stage of the calculations that are currently being performed. The sample data contain the input DEM, masks and coastline for each raster specifically. After running the script, the output of each sample file will be saved in the respective sample directory in the output folder which will be automatically generated.

Once all the data have been correctly recalculated, we can use the GUI for visualisation or Jupyter Notebook tools in for further analysis. The paths in these programs are set by default to the data in the demo directory, but the scripts support both absolute and relative paths. .

## ```Most common problems```
- no Rtree tool installed on the system,
- no GDAL tool installed on the system,
- versions conflict between the system GDAL tool and the GDAL package for Python,
- incorrectly entered paths to data in configuration files,
- incorrect datum (for example, input *.shp files with shoreline or trimming area do not have *.prj files or data in *.prj is incorrect).
- different sizes of DEM files
- incorrect elevation parameters in DEM files
- incorrect transect lengths

We recommend that the first analyses be performed on a smaller number of transects (e.g., 10-20) to check the accuracy of calculations on the new data. With correct results, more complex analyses can be run. 
On the Demo files, calculations were performed for about 1000 transects on each file.   


## Project Status
This application is under active development. 
Upcoming features may include: 
- Additional data visualisations and modules.

## Authors
Jakub Śledziowski, Witold Maćków, Andrzej Łysko, Paweł Terefenko, Andrzej Giza and Kamran Tanwari as a team in Baltic Coastal Monitoring Team

## Citation
> Coming soon.

## License
MIT License
