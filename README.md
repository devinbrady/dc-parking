# DC Parking

A shapefile with one point for every estimated Residential Permit Parking (RPP) spot in DC: 

* [GeoJSON](output/estimated_rpp_spots.geojson)
* [CSV](output/estimated_rpp_spots.csv)

## Purpose

The goal of this project is to estimate the total number of parking spots in the RPP program and count them by other geographies, such as ward, ANC single member district, census block, and neighborhood. 

## Process

This data is an estimate based off of street segments in the RPP data published by Open Data DC. Each segment is divided into points 21 feet apart (I measured distances between a sample of cars on an RPP block and 21 feet was a good midpoint). 

Then, each point was moved to the side of the street that the data indicated was open to parking (odd, even, or both). Odd and even doesn't necessarily correspond to the correct side of the street, it was picked at random. 

Next, I built buffers around each of the exclusion points and removed all of the parking spots that fell into one of the buffers. 

## Counts

See the notebook [Counts](Counts.ipynb) for parking spots by ward and total area. 

## Exclusions

Parking spots that are near other points, defined by Open Data DC shapefiles, are excluded. 

* Street intersections: 50 foot radius
* Fire hydrants: 20 foot radius
* Parking meters: 50 foot radius

## Data Sources

### Open Data DC

* [Residential Parking Permit Blocks](https://opendata.dc.gov/datasets/residential-parking-permit-blocks)
* [Fire Hydrants](https://opendata.dc.gov/datasets/fire-hydrants)
* [Parking Meters](https://opendata.dc.gov/datasets/parking-meters)
* [Street Segments](https://opendata.dc.gov/datasets/street-segments)
* [Advisory Neighborhood Commission](https://opendata.dc.gov/datasets/advisory-neighborhood-commissions-from-2013)
* [ANC Single Member District](https://opendata.dc.gov/datasets/single-member-district-from-2013)

### TIGER/Line

* [2019 Census Block](https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2019&layergroup=Blocks+%282010%29)