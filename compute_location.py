import logging
import math


from kapacitor.udf import udf_pb2
from kapacitor.udf.agent import Agent, Handler


from location_algo import get_lat_long_for_receiver
from location_algo import calculate_location

ACCURACY_ACCURATE = 'ACCURATE'
ACCURACE_PRESENCE = 'PRESENCE'
ACCURACY_UNKNOWN = 'UNKNOWN'

LOW_RSSI_THRESHOLD = -70
MAX_RSSI_THRESHOLD = -40
MIN_NUMBER_TRILATERATION=9
CHIRP_PERIOD   = 2

logging.basicConfig(filename='/home/akaushik/piri-location-engine/compute_location.log',level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger()

class ChirpEventHandler(Handler):


    class chirpevent(object):
        def __init__(self):
            self._entries = []

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

        max_rssi = -96
        receiver_tobeused_presence = ""
        response = udf_pb2.Response()
        response.point.fieldsString["accuracy"] = ACCURACY_UNKNOWN

        # uniqueChirpEvents
        # uniqueChirpEvents[001122334455] = -45
        uniqueChirpEvents = {}
        max_rssi = -255
        at_least_one_strong = False
        lat = 0
        lon = 0

        for chirp in chirp_events:
            new_rssi = chirp.fieldsDouble['rssi']
            receiver = chirp.fieldsString['receiver']
            if receiver in uniqueChirpEvents.keys():
               old_rssi = uniqueChirpEvents[receiver]
               if chirp.fieldsDouble['rssi'] > old_rssi:
                   if new_rssi > LOW_RSSI_THRESHOLD:
                     uniqueChirpEvents[receiver]= chirp.fieldsDouble['rssi']

               if new_rssi > LOW_RSSI_THRESHOLD:
                    at_least_one_strong = True

               if new_rssi > max_rssi:
                    max_rssi = new_rssi
                    receiver_tobeused_presence = chirp.fieldsString['receiver']
            else:
             uniqueChirpEvents[receiver] = new_rssi

        logger.debug('unique chirp events ares %s',uniqueChirpEvents)
        if not at_least_one_strong:
            response.point.fieldsString["accuracy"] = ACCURACE_PRESENCE
            #get lat long for receiver_tobeused_presence
            lat,lon = get_lat_long_for_receiver(receiver_tobeused_presence)
            self._agent.write_response(response)
            return

        # at this stage we only have unique events for which we have RSSI better than LOW_THRESHOLD
        response.point.fieldsString["accuracy"] = ACCURACY_ACCURATE

        #If there is only one chirp
        if len(uniqueChirpEvents) == 1:
            lat, long = get_lat_long_for_receiver(receiver_tobeused_presence)
        else:
            # uniqueChirpEvents has the unique events
            logger.debug("applying location algorithm")
            lat,lon = calculate_location(uniqueChirpEvents)

        response.point.fieldsDouble["lat"] = lat
        response.point.fieldsDouble["lon"] = lon
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
