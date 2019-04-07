# BLE location engine using Kapacitor UDF function
------------------------------------------------

Location engine calculates the long and lat of asset using trilateration. 

This is based on the assumption that asset would send chirp using BLE/WiFi and there would be receivers to listen for these chirps.Receivers would report out the chirp's RSSI value. Receivers would be deployed at well defined location (lat and long is known to the system).

This is implemented as a TASK in Kapacitor on top of influxDB and computes location and stores Asset Location Events in the influxDB


How Location Engine works?
-----------------------------
Location Engine is implemented as a kapacitor task.  It is configured for batch mode processing of all events in “last         XXX” seconds for each Monitored Asset.  The XXX depends upon each asset and its “Chirp Period”. 

	If the Chirp Period is less than 1 second, XXX will be 2

	If the Chirp Period is a larger number such as 15 seconds, XXX will be 16 seconds.

	We always add additional 1 second to get all chirps to take care of asset location.  This number is fine tuned in production

Algorithm
------------
At start each asset is stored in influx database as “Accuracy” Location UNKNOWN.
Received N messages in last XXX seconds for this asset.
Use this to triangulate and compute location and store the “Asset Location Event” in influxDB in Asset Location Data 

Compute location: 
-------------------
If only one chirp then 

	If RSSI is very low then we mark “Accuracy” as Presence only

	If RSSI is very strong then we use that receiver as the location

If two or more chirps then we can report “closest” receiver location or “trilaterate” it

	Use the Received RSSI values and the asset configured RSSI value for trilateration

	If all are “very low” RSSI values then we mark “Accuracy” as Presence only

	We trilaterate only among the “not very low” RSSI values.


We will start following task “compute_location” for every asset that has “ALERT if Asset Presence LOST” configured.


How to start the template?
-----------------------------

{
    "asset_mac_address": {"type" : "string", "value" : "112233445566" }
}


kapacitor define compute_location -template compute_location -vars asset_vars.json -dbrp my_building.assets





sample compute_location.tck

var chirp_events = batch

	    |query('SELECT * FROM my_building.autogen.asset_chirp_events where asset_mac_address=\'{asset_mac_address}\'')

		 .period(100m)

		 .every(2m)


chirp_events

	    @tComputeLocation()

	         .field('asset_mac_address')

	         .field('receiver')

		     .field('rssi')

		     .field('time')

		|influxDBOut()

             .database('my_building')

             .retentionPolicy('autogen')

             .measurement('assets_location_events')




Now create following bash script to create task

create_task.sh
=========================================================================================================================

cp compute_location.tick compute_location_$1.tick

sed -i "s/{asset_mac_address}/$1/g" compute_location_$1.tick

kapacitor define-template compute_location_template -tick compute_location_$1.tick

kapacitor define compute_location -template compute_location_template -vars asset_vars.json  -dbrp my_building.autogen
==========================================================================================================================

Execute script

./create_task.sh <mac address of asset to be tracked>

Configure kapacitor conf file to include UDF definition


Create UDF function compute_location.py
-------------------------------------------

import logging

import math


from kapacitor.udf import udf_pb2

from kapacitor.udf.agent import Agent, Handler



logging.basicConfig(filename='/home/akaushik/piri-location-engine/compute_location.log',level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(name)s: %(message)s')

logger = logging.getLogger()


class ChirpEventHandler(Handler):

    class chirpevent(object):

        def __init__(self):

            self._entries = []


        def calculate_distance(self,  rssi,  freqInMHz=2142):

            exp = (27.55 - (20 * math.log10(freqInMHz)) + math.fabs(rssi)) / 20.0

            return math.pow(10.0, exp)



        def reset(self):

            self._entries = []


        def update(self, point):

            self._entries.append((point))


        def get_chirp_events(self):

            return self._entries




    def __init__(self, agent):

        self._agent = agent

        self._field = None

        self._begin_response = None

        self._state = ChirpEventHandler.chirpevent()

        self._size = 0


    def info(self):

        response = udf_pb2.Response()

        response.info.wants = udf_pb2.BATCH

        response.info.provides = udf_pb2.BATCH


        response.info.options['field'].valueTypes.append(udf_pb2.STRING)


        logger.info("info")

        return response


    def init(self, init_req):

        success = True

        msg = ''

        size = 0

        logger.info("init_req %s",init_req)


        for opt in init_req.options:

            if opt.name == 'field':

                self._field = opt.values[0].stringValue


        if self._field is None:

            success = False

            msg += ' must supply a field name'


        response = udf_pb2.Response()

        response.init.success = success

        response.init.error = msg[1:]

        return response


    def snapshot(self):

        response = udf_pb2.Response()

        response.snapshot.snapshot = ''

        return response


    def restore(self, restore_req):

        response = udf_pb2.Response()

        response.restore.success = False

        response.restore.error = 'not implemented'

        return response


    def begin_batch(self, begin_req):

        logger.debug("Begin request is : %s",begin_req)

        self._state.reset()


        # Keep copy of begin_batch

        response = udf_pb2.Response()

        response.begin.CopyFrom(begin_req)

        self._begin_response = response



    def point(self, point):


        value = point.fieldsString[self._field]

        self._state.update(point)

        logger.debug("Point is %s", str(point))


    def end_batch(self, end_req):


        logger.debug("end request %s",end_req)


        chirp_events = self._state.get_chirp_events()


        max_rssi = -100

        receiver_with_maxrssi = ""


        for chirp in chirp_events:

            response = udf_pb2.Response()

            response.point.fieldsString["asset_mac_address"] = chirp.fieldsString['asset_mac_address']

            response.point.time = chirp.time

            logger.debug("rssi value is %s",chirp.fieldsDouble['rssi'])

            if max_rssi <  chirp.fieldsDouble['rssi']:

                max_rssi = chirp.fieldsDouble['rssi']

                receiver_with_maxrssi = chirp.fieldsString['receiver']




        #calculate distance in meter..Hard coded frequency as of now. we need to replace with actual value

        distance  = self._state.calculate_distance(max_rssi, 2142)


        #trilateration algorithm goes here---Replacement for following algorithm for higher accuracy


        #Now pickup the following values same as receiver's address [receiver_with_maxrssi]

        #fetch co-ordinate of receiver with MAX RSSI


        response.point.fieldsString["building"] = 'my_building'

        response.point.fieldsString["floor"] = 'first'

        response.point.fieldsString["zone"] = 'kitchen'

        response.point.fieldsDouble["gps_x"] = 37.368832

        response.point.fieldsDouble["gps_y"] = -122.036346

        response.point.fieldsDouble["distance"] = distance

        response.point.fieldsString["accuracy"] = 'TRUE'

        logger.debug("Response is %s", response)

        self._agent.write_response(response)


if __name__ == '__main__':

    a = Agent()

    h = ChirpEventHandler(a)

    a.handler = h


    logger.info("Starting Agent")

    a.start()

    a.wait()

    logger.info("Agent finished")



Modify /etc/kapacitor/kapacitor.conf
----------------------------------------------

Add following entry in UDF section



[udf]

# Configuration for UDFs (User Defined Functions)

[udf.functions]

   [udf.functions.tComputeLocation]

       # Run python

        prog = "/usr/bin/python2"

        # Pass args to python

        # -u for unbuffered STDIN and STDOUT

        # and the path to the script

        args = ["-u", "<path>/compute_location.py"]

        # If the python process is unresponsive for 10s kill it

        timeout = "10s"

        # Define env vars for the process, in this case the PYTHONPATH

        [udf.functions.tComputeLocation.env]

            PYTHONPATH = "/tmp/kapacitor_udf/kapacitor/udf/agent/py"

            PYTHONIOENCODE = "latin1"

    




Start all the required process
------------------------------------

Start kapacitor and influxdb

sudo kapacitord -config /etc/kapacitor/kapacitor.conf 

sudo influxd


At this stage, every asset has a location in the influxDB.
