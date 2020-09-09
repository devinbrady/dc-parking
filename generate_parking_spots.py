
import sys
import math
import pyproj
import numpy as np
import pandas as pd
from tqdm import tqdm
import geopandas as gpd
from pathlib import Path
from datetime import datetime
from shapely.geometry import Point
from geopy.distance import lonlat, distance


# Use this projection for measuring distances in meters
# https://octo.dc.gov/page/coordinate-system-standards
maryland_crs = ('epsg', '26985')

# Use WGS84 for saving GeoJSON for display in QGIS
output_crs = ('epsg', '4326')


one_foot_in_meters = 0.3048


def map_block_side(blk_side_series):
    """
    Map the block side letters to their definition
    """

    return blk_side_series.map({
        'AO': 'address only'
        , 'B': 'both sides'
        , 'V': 'even side'
        , 'O': 'odd side'
        , 'S': 'single building'
    })



def point_along_line(start_point, end_point, meters_from_start):
    """
    Return a point that is one the line between start_point and end_point, 
    meters_from_start away from the start_point
    
    Points are (x,y) (lon,lat)
    """
    
    segment_length = distance(lonlat(*start_point), lonlat(*end_point)).meters
    
    ratio_of_distances = meters_from_start / segment_length
    
    destination_point = (
        ((1 - ratio_of_distances) * start_point[0]) + (ratio_of_distances * end_point[0])
        , ((1 - ratio_of_distances) * start_point[1]) + (ratio_of_distances * end_point[1])
    )
    
    return destination_point



def cut_street_into_points(street):
    """
    """

    meters_per_car = 21 * one_foot_in_meters

    geom = [Point(xy) for xy in street['geometry'].coords]
    geom_idx = 0
    parking_spots = [geom[0].coords[0]]

    meters_remaining_for_current_spot = meters_per_car

    while geom_idx < (len(geom) - 1):

        segment_start = geom[geom_idx].coords[0]
        segment_end = geom[geom_idx + 1].coords[0]
        segment_length = distance(lonlat(*segment_start), lonlat(*segment_end)).meters

        while meters_remaining_for_current_spot < segment_length:

            new_spot = point_along_line(segment_start, segment_end, meters_remaining_for_current_spot)
            parking_spots += [new_spot]
            segment_start = new_spot

            segment_length -= meters_remaining_for_current_spot

            meters_remaining_for_current_spot = meters_per_car

        # If this segment is too short for even one parking spot, 
        # OR there is not enough segment remaining for another parking spot,
        # decrement the meters remaining by leftover segment length and iterate to the next segment.
        meters_remaining_for_current_spot -= segment_length

        geom_idx += 1


    return [Point(p) for p in parking_spots]



def street_blocks_to_parking_spots():
    """
    Read in a shapefile containing the RPP blocks and save out a GeoJSON
    containing one point for every possible parking space on each block. 
    """
    
    rpp = gpd.read_file('input/Residential_Parking_Permit_Blocks-shp/Residential_Parking_Permit_Blocks.shp')
    rpp = drop_duplicate_geometries(rpp, print_counts=True)
    # rpp = rpp.to_crs(maryland_crs)
    
    # Rename block sides
    rpp['block_side'] = rpp['BLK_SIDE'].map({
        'AO': 'address only'
        , 'B': 'both sides'
        , 'V': 'even side'
        , 'O': 'odd side'
        , 'S': 'single building'
    })

    parking_dict = {}

    street_width = 10 # meters
    street_width_radians = 0.00003

    for idx, street in tqdm(rpp.iterrows(), total=len(rpp)):

        if street['OBJECTID'] == 1973107:
            # Multiple line segments on this street
            # rpp[rpp['OBJECTID'] == 1973107]
            continue

        # if idx > 10:
        #     break
            
        # if street['OBJECTID'] not in [
        #         1971375 # California
        #         , 1972138 # 19th
        #         , 1969724 # Mintwood Place
        #     ]: 
            continue

        try:
            street_points = cut_street_into_points(street)
        except Exception as e:
            bad_objectid = street['OBJECTID']
            print(f'OBJECTID {bad_objectid} causes error: {e}')
            continue

        start_coord = street['geometry'].coords[0]
        start_lon = start_coord[0]
        start_lat = start_coord[1]
        end_coord = street['geometry'].coords[-1]
        end_lon = end_coord[0]
        end_lat = end_coord[1]

        geodesic = pyproj.Geod(ellps='WGS84')
        street_heading, _, _ = geodesic.inv(start_lon, start_lat, end_lon, end_lat)
        
        heading_right = (street_heading + 90)
        offset_right_x = math.sin(math.radians(heading_right)) * street_width_radians
        offset_right_y = math.cos(math.radians(heading_right)) * street_width_radians

        heading_left = (street_heading - 90)
        offset_left_x = math.sin(math.radians(heading_left)) * street_width_radians
        offset_left_y = math.cos(math.radians(heading_left)) * street_width_radians

        street_series = gpd.GeoSeries(street_points)
        # todo: determine which is side is even and odd based off of heading

        if street['block_side'] == 'both sides':
            street_series_odd = street_series.translate(xoff=offset_right_x, yoff=offset_right_y)
            street_series_even = street_series.translate(xoff=offset_left_x, yoff=offset_left_y)

            street_series_combined = pd.concat([street_series_odd, street_series_even], ignore_index=True)

        elif street['block_side'] == 'even side':
            street_series_combined = street_series.translate(xoff=offset_left_x, yoff=offset_left_y)

        elif street['block_side'] == 'odd side':
            street_series_combined = street_series.translate(xoff=offset_right_x, yoff=offset_right_y)

        else:
            continue


        temp_df = pd.DataFrame()
        temp_df['geometry'] = street_series_combined
        temp_df['source_street_objectid'] = street['OBJECTID']
        temp_df['block_side'] = street['block_side']

        parking_dict[street['OBJECTID']] = temp_df



    df_dict = {}
    for d in parking_dict:
        df_dict[d] = pd.DataFrame(parking_dict[d], columns=['geometry'])

    parking_df = pd.concat(df_dict).reset_index()
    parking_df.rename(columns={'level_0': 'source_street_objectid'}, inplace=True)
    parking_df.drop('level_1', axis=1, inplace=True)
    parking_df = parking_df.reset_index()
    parking_df['parking_spot_id'] = parking_df['index'] + 1
    parking_df.drop('index', axis=1, inplace=True)

    parking_gdf = gpd.GeoDataFrame(parking_df)

    parking_gdf_output = parking_gdf #.to_crs(output_crs)
    parking_gdf_output.to_file('output/parking_spots.geojson', driver='GeoJSON')

    print('Number of parking spots: {:,}'.format(len(parking_gdf)))



def street_segments_to_intersections(input_file):
    """
    Return intersection for every road segment in input_file
    """

    streets = gpd.read_file(input_file)
    streets_uu = streets.unary_union

    intersections = streets_uu.intersection(streets_uu)

    intersections_gdf = gpd.GeoDataFrame(intersections, columns=['geometry'])
    intersections_gdf = drop_duplicate_geometries(intersections_gdf, print_counts=True)
    intersections_gdf.to_file('output/street_intersections.geojson', driver='GeoJSON')



def drop_duplicate_geometries(gdf, print_counts=False):
    # Drop duplicates. From https://github.com/geopandas/geopandas/issues/521
    
    if print_counts:
        print('Dropping duplicates... {:,} '.format(len(gdf)), end='--> ')
    
    G = gdf['geometry'].apply(lambda geom: geom.wkb)
    gdf = gdf.loc[G.drop_duplicates().index]
    
    if print_counts:
        print('{:,}'.format(len(gdf)))
    
    return gdf



def exclude_parking_spots_from_point_buffers(
    exclusion_points, output_file, sample=False):
    """
    Given an input GeoJSON of parking spaces, save out a GeoJSON of parking spaces
    that do not fall within the buffer of any of the input_points
    
    Takes 11 minutes to run all three exclusions

    todo: multithread this
    """
    
    parking_gdf = gpd.read_file('output/parking_spots.geojson')
    parking_gdf = drop_duplicate_geometries(parking_gdf)
    parking_gdf = parking_gdf.to_crs(maryland_crs)
    
    if sample:
        parking_gdf = parking_gdf.sample(1000)

    exclusion_dict = {}
    for ep in exclusion_points:
        temp = gpd.read_file(ep)
        temp = drop_duplicate_geometries(temp)
        temp = temp.to_crs(maryland_crs)

        # Buffer Resolution * 4 => sides of the circle
        buff = temp.geometry.buffer(exclusion_points[ep], resolution=3)

        bdf = gpd.GeoDataFrame(buff, columns=['geometry'])
        exclusion_dict[ep] = bdf.to_crs(output_crs)
        
        buffer_output_file = 'output/' + Path(ep).stem + '_buffer.geojson'
        exclusion_dict[ep].to_file(buffer_output_file, driver='GeoJSON')
        print('Buffer saved to: ' + buffer_output_file)

    exclusion_gdf = pd.concat(exclusion_dict)
    exclusion_gdf = exclusion_gdf.to_crs(maryland_crs)
    
    buffer_uu = exclusion_gdf.unary_union
    parking_gdf_uu = parking_gdf.unary_union

    pbud = parking_gdf_uu.difference(buffer_uu)

    parking_spots_no_exclusions = gpd.GeoDataFrame(pbud, columns=['geometry'])
    parking_spots_no_exclusions.crs = maryland_crs
    # todo: join this with the original geodataframe to get street name, parking spot id

    parking_spots_no_exclusions = drop_duplicate_geometries(parking_spots_no_exclusions, print_counts=True)

    parking_spots_no_exclusions_wgs84 = parking_spots_no_exclusions.to_crs(output_crs)
    parking_spots_no_exclusions_wgs84.to_file(output_file, driver='GeoJSON')
    
    print('Number of parking spots: {:,}'.format(len(parking_spots_no_exclusions_wgs84)))
    print('GeoJSON saved to: ' + output_file)



def add_fields_from_original_shapefile():
    """
    Join narrowed shapefile to original shapefile by geometry, 
    and add fields like street name to the narrowed geodataframe
    """

    parking_spots = gpd.read_file('output/parking_spots.geojson')
    parking_spots_narrowed = gpd.read_file('output/parking_spots_narrowed.geojson')

    parking_spots['source_street_objectid'] = parking_spots['source_street_objectid'].round().astype(str)
    parking_spots['parking_spot_id'] = parking_spots['parking_spot_id'].round().astype(str)


    parking_spots['geo_str'] = (
        parking_spots['geometry'].x.round(8).astype(str)
        + ', '
        + parking_spots['geometry'].y.round(8).astype(str)
    )

    parking_spots_narrowed['geo_str'] = (
        parking_spots_narrowed['geometry'].x.round(8).astype(str)
        + ', '
        + parking_spots_narrowed['geometry'].y.round(8).astype(str)
    )

    ps_joined = pd.merge(
        parking_spots_narrowed
        , parking_spots[['geo_str', 'parking_spot_id', 'source_street_objectid']]
        , how='inner', on='geo_str'
    )

    rpp = gpd.read_file('input/Residential_Parking_Permit_Blocks-shp/Residential_Parking_Permit_Blocks.shp')

    rpp['block_side'] = map_block_side(rpp['BLK_SIDE'])
    rpp['source_street_objectid'] = rpp['OBJECTID'].round().astype(str)

    rpp_columns = [
        'source_street_objectid'
        , 'REGISTERED'
        , 'STREETTYPE'
        , 'QUADRANT'
        , 'BLOCKNUMBE'
        , 'WARD'
        , 'BLKSTREET'
        , 'block_side'
    ]

    parking_rpp = pd.merge(ps_joined, rpp[rpp_columns], how='inner', on='source_street_objectid')
    parking_rpp = parking_rpp.drop('geo_str', axis=1)
    parking_rpp = parking_rpp.rename(columns={
        'REGISTERED': 'street_name'
        , 'STREETTYPE': 'street_type'
        , 'BLOCKNUMBE': 'block_number'
        })
    # parking_rpp['WARD'] = parking_rpp['WARD'].astype(int)
    parking_rpp.columns = [c.lower() for c in parking_rpp.columns]


    output_file = 'output/estimated_rpp_spots.geojson'
    parking_rpp.to_file(output_file, driver='GeoJSON')
    print(f'Output saved to: {output_file}')



def geojson_to_csv(input_geojson):
    """
    Save a copy of a GeoJSON file as a CSV
    """

    gdf = gpd.read_file(input_geojson)
    
    gdf['longitude'] = gdf['geometry'].x
    gdf['latitude'] = gdf['geometry'].y

    columns_to_csv = [c for c in gdf if c != 'geometry']
    output_filename = input_geojson.replace('.geojson', '.csv')
    gdf.to_csv(output_filename, index=False)
    print(f'CSV saved to: {output_filename}')



if __name__ == '__main__':

    street_blocks_to_parking_spots()

    # street_segments_to_intersections('input/Street_Segments-shp/Street_Segments.shp')

    exclude_parking_spots_from_point_buffers(
        exclusion_points = {
            'input/street_intersections.geojson': 50 * one_foot_in_meters
            , 'input/Fire_Hydrants-shp/Fire_Hydrants.shp': 20 * one_foot_in_meters
            , 'input/Parking_Meters-shp/Parking_Meters.shp': 50 * one_foot_in_meters
        }
        , output_file = 'output/parking_spots_narrowed.geojson'
        , sample = False
    )

    add_fields_from_original_shapefile()

    geojson_to_csv('output/estimated_rpp_spots.geojson')


