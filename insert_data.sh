# add asset chirp events into measurement
while [ 1 ]
do
	current_time=`date +%s%N | cut -b1-13`
	current_time=$(expr $current_time \* 1000 \* 1000)
	rssi=$(( ( RANDOM % 10 )  + 1 ))
	rssi=$(expr $rssi - 60)
	echo $rssi
	echo "Inserting data into kontakt\n"
	curl -i -XPOST "http://localhost:8086/write?db=kontakt" --data-binary 'asset_chirp_events,asset_mac_address=001122334456,receiver=aabbccddeeff rssi='"$rssi"' '"$current_time"''
	sleep 2
	current_time=`date +%s%N | cut -b1-13`
	current_time=$(expr $current_time \* 1000 \* 1000)
	rssi=$(( ( RANDOM % 10 )  + 1 ))
	rssi=$(expr $rssi - 60)
	curl -i -XPOST "http://localhost:8086/write?db=kontakt" --data-binary 'asset_chirp_events,asset_mac_address=001122334456,receiver=aabbccddeefg rssi='"$rssi"' '"$current_time"''
	sleep 2
	current_time=`date +%s%N | cut -b1-13`
	current_time=$(expr $current_time \* 1000 \* 1000)
	rssi=$(( ( RANDOM % 10 )  + 1 ))
	rssi=$(expr $rssi - 60)
	curl -i -XPOST "http://localhost:8086/write?db=kontakt" --data-binary 'asset_chirp_events,asset_mac_address=001122334456,receiver=aabbccddeefh rssi='"$rssi"' '"$current_time"''
	sleep 2
done

