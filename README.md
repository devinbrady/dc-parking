# DC Parking

A shapefile with one point for every estimated Residential Permit Parking (RPP) spot in DC: 

* [GeoJSON](output/estimated_rpp_spots.geojson)
* [CSV](output/estimated_rpp_spots.csv)

This data is an estimate based off of street segments in the RPP data published by Open Data DC. 

## Counts

See the notebook [Counts](Counts.ipynb) for parking spots by ward and total area. 

## Exclusions

Parking spots that are near other points, defined by Open Data DC shapefiles, are excluded. 

* Street intersections: 50 foot radius
* Fire hydrants: 20 foot radius
* Parking meters: 50 foot radius

## Data Sources

[Residential Parking Permit Blocks
](https://opendata.dc.gov/datasets/residential-parking-permit-blocks)
