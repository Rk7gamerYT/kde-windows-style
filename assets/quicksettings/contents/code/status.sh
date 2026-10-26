#!/bin/sh
# One line of key=value pairs with the state the quick settings flyout shows.
export LC_ALL=C.UTF-8
wifi=$(nmcli radio wifi 2>/dev/null)
ssid=$(nmcli -t -f active,ssid dev wifi 2>/dev/null | sed -n 's/^yes://p' | head -n1)
wired=$(nmcli -t -f type,state dev 2>/dev/null | grep -c '^ethernet:connected$')
bt=$(bluetoothctl show 2>/dev/null | sed -n 's/^\s*Powered: //p' | head -n1)
hasbt=$(bluetoothctl list 2>/dev/null | grep -c Controller)
airplane=$(rfkill -rn -o SOFT 2>/dev/null | grep -q '^unblocked' && echo no || echo yes)
volume=$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | grep -o '[0-9]*%' | head -n1 | tr -d %)
mute=$(pactl get-sink-mute @DEFAULT_SINK@ 2>/dev/null | grep -q ': yes$' && echo yes || echo no)
night=$(kreadconfig6 --file kwinrc --group NightColor --key Active --default false)
dnd=$(kreadconfig6 --file plasmanotifyrc --group DoNotDisturb --key Until)
echo "wifi=$wifi|ssid=$ssid|wired=$wired|bt=$bt|hasbt=$hasbt|airplane=$airplane|volume=${volume:-0}|mute=$mute|night=$night|dnd=$dnd"
