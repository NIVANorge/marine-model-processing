# eswm-bolgemodell

1 Import Raster:

r.in.gdal input=raster.tif output=raster

2 Vectorize (option -s leads to slightly smoothed 45-degree edges):

r.to.vect -s input=raster output=vector_blue feature=area

3 Generalize with Douglas to get rid of excessive points:

4. Substract land