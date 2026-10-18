DOUBLE-DIFFERENCE EARTHQUAKE CATALOG FOR NORTHERN CALIFORNIA, 1984-2021
-----------------------------------------------------------------------

NCAeqDD.v202112.1 --- Version: 202112.1 --- June, 2022

Felix Waldhauser and David Schaff
Lamont-Doherty Earth Observatory
Columbia University

CONTACT: felixw@ldeo.columbia.edu

INFO and DOWNLOAD: http://nocalDD.ldeo.columbia.edu/catalog

OVERVIEW:
This file includes high-precision hypocenter locations for 879,626 
earthquakes recorded between January 1984 - December 2021 by stations of 
the Northern California Seismic System (NCSS). Relative locations were 
computed from a comprehensive double-difference inversion of a combination 
of NCSS phase pick data and cross-correlation differential times measured 
from correlated seismograms. This catalog is an update of the original DD 
catalog (1984-2003) described in detail in Waldhauser and Schaff (2008) and 
released as NCAeqDD.1984-2003.v1.0 in January 2008. Similar computational 
procedures and parameter settings were used to generate this update (*).

Important: This catalog includes events that were recorded by 6 or more 
stations (in previous catalogs that threshold was 7). Ongoing efforts 
are aimed at lowering the number of required recording stations in order 
to improve the completeness of the catalog.  However, the primary goal of 
this project is to produce earthquake catalogs of highest possible resolution.

(*) IMPORTANT NOTE: Different from previous versions of the catalog, the 
current version is based on inital NCSN hypocenter depths that are referenced 
to the Geoid. This catalog therefore includes events with negative depths 
(those above Geoid datum). Previous catalogs had depths referenced to the 
surface of the model used for locating the events. That surface was 
assigned a depth of zero and determined from the the average elevation of 
the five closest stations. See http://nocalDD.ldeo.columbia.edu/catalog/
for further information.
 
CITATION:
This is version v202112.1 of the NCAeqDD catalog series and should be 
referenced as Waldhauser and Schaff (2008) with version number indicated.

VERSION HISTORY:
NCAeq_DD.1984-2003.v1.0	 ---   Released Jan, 2008 Depths referenced to
                                                   NCSN model depth datum
NCAeqDD.v200812.1.0	 ---   Released Jun, 2010         "
NCAeqDD.v200812.1.1    	 ---   Released Jul, 2010         "
NCAeqDD.v200912.1    	 ---   Released Jun, 2011         "
NCAeqDD.v201112.1    	 ---   Released Jun, 2013         "
NCAeqDD.v201412.1    	 ---   Released Nov, 2015 	  " 
NCAeqDD.v201412.2    	 ---   Released Jan, 2016  Depths referenced to  
                                                   Geoid depth(this file)
NCAeqDD.v201912.1    	 ---   no release	          "
NCAeqDD.v202112.1    	 ---   Released Jun, 2022  	  "    (this file)

REFERENCES:
Waldhauser, F. and D.P. Schaff (2008), Large-scale relocation of two 
   decades of Northern California seismicity using cross-correlation 
   and double-difference methods, J. Geophys. Res., 113, B08311, 
   doi:10.1029/2007JB005479.

See also:
Schaff, D.P. and F. Waldhauser (2005), Waveform Cross-Correlation-Based 
   Differential Travel-Time Measurements at the Northern California 
   Seismic Network, Bull.  Seism. Soc. Am., 95, 2446-2461. 
Waldhauser F. and W.L. Ellsworth (2000), A double-difference earthquake 
   location algorithm: Method and application to the northern Hayward 
   fault, Bull. Seism. Soc. Am., 90, 1353-1368. 
Waldhauser, F. (2009), Near-real-time double-difference event location using 
   long-term seismic archives, with application to Northern California, 
   Bull. Seism. Soc. Am., 99, 2736-2748, https://doi.org/10.1785/0120080294
   [http://ddrt.ldeo.columbia.edu]

DATA SOURCES:
U.S. Geological Survey, Menlo Park; University of California, Berkeley; 
Northern California Earthquake Data Center (NCEDC) and the Northern 
California Seismic Network (NCSN); California Institute of Technology; 
University of Nevada, Reno; California Division of Water Resources; 
University of Utah; University of Southern California. 
Seismic archives were obtained from the NCEDC.

FORMAT DESCRIPTION:
DATE......... Year, Month, Day
TIME......... Hour, Minute, Second
LAT/LON...... Location
DEP.......... Depth [km]
EH1/EH2/AZ... Horizontal major/minor axis [km] and azimuth of the 95% 
              relative location error ellipses. (-1 if not available).
EV........... Vertical relative location error [km] at the 95%
              confidence level. (-1 if not available).
MAG.......... Magnitude, ML, as listed in the NCSN catalog. 
ID........... CUSP event ID.


   DATE        TIME         LAT          LON         DEP     EH1     EH2   AZ    EZ    MAG       ID
-----------------------------------------------------------------------------------------------------
