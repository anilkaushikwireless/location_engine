cp compute_location.tick compute_location_$1.tick
sed -i "s/{asset_mac_address}/$1/g" compute_location_$1.tick
kapacitor define-template compute_location_template -tick compute_location_$1.tick
kapacitor define compute_location -template compute_location_template -vars asset_vars.json  -dbrp my_building.autogen

