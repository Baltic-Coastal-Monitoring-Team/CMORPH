from os.path import join, basename


def parse(cfg, fname):
    return eval(f"_{fname}(cfg)")


def _get_DEM(cfg):
    base_path = cfg["paths"]["base"]
    return (
        join(base_path, cfg["paths"]["input"]["dem"]),  # dem_path
        join(base_path, cfg["paths"]["output"]["dem_cropped"]),  # cropped_path
        join(base_path, cfg["paths"]["output"]["dem_slope"]),  # slope_path
        join(base_path, cfg["paths"]["db"]),  # db
        cfg["db_layers"]["transects"],  # transects_layer
        cfg["db_layers"]["buffers"],  # buffers_layer
        cfg["crs"],
        (
            cfg["parameters"]["buffer_width"]
            if "buffer_width" in cfg["parameters"]
            else cfg["parameters"]["transect_distance"] / 2
        ),  # buffer_width == transect_distance / 2
    )


def _generate_transects(cfg):
    return (
        join(cfg["paths"]["base"], cfg["paths"]["db"]),  # db
        cfg["crs"],
        cfg["db_layers"]["coastline"],  # line_layer
        cfg["db_layers"]["points"],  # points_layer
        cfg["db_layers"]["transects"],  # transects_layer
        cfg["parameters"]["transect_distance"],  # transect_distance
        cfg["parameters"]["transect_length"],  # transect_length
    )


def _generate_profiles(cfg):
    base_path = cfg["paths"]["base"]
    return (
        cfg["crs"],
        join(base_path, cfg["paths"]["input"]["dem"]),  # dem_path
        join(base_path, cfg["paths"]["output"]["dem_cropped"]),  # cropped_path
        join(base_path, cfg["paths"]["output"]["dem_slope"]),  # slope_path
        join(base_path, cfg["paths"]["output"]["profiles_whole"]),  # profile_path
        join(base_path, cfg["paths"]["db"]),  # db
        cfg["db_layers"]["profiles"],  # profiles_layer
        cfg["db_layers"]["transects"],  # transects_layer
        cfg["parameters"]["profile_resolution"],  # resolution
        cfg["csv"],  # csv
    )


def _crop_profiles(cfg):
    base_path = cfg["paths"]["base"]
    return (
        cfg["crs"],
        join(base_path, cfg["paths"]["input"]["crop"]),  # buffer_path
        join(base_path, cfg["paths"]["output"]["profiles_whole"]),  # in_profile_path
        join(base_path, cfg["paths"]["output"]["profiles_cropped"]),  # out_profile_path
        cfg["csv"],  # csv
    )
