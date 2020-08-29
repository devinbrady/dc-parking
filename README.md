# DC Parking

A shapefile with one point for every estimated Residential Permit Parking (RPP) spot in DC: [output/parking_spots_narrowed.geojson](output/parking_spots_narrowed.geojson)

This data is an estimate based off of street segments that are identified as being in the RPP program. 

## Exclusions

Parking spots that are near other points, defined by Open Data DC shapefiles, are excluded. 

* Street intersections: 50 foot radius
* Fire hydrants: 20 foot radius
* Parking meters: 50 foot radius