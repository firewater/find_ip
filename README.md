# find_ip
Get IP info and display on a map.

find_ip is a Python-based client-side web application that pings every IPv4 address, collects some information about it, then displays its location on a Google Map: 

...insert image...

Since there are 4,294,967,296 IPv4 addresses, the script uses Python's multiprocessing module to ping several hosts in parallel. The more cores available, the faster the pinging. Upon starting the script, it will report the number of available CPUs/cores.

After pinging, information about the IP address is gathered from ip-api.com then written to a local SQLite database. That information is pushed out to your web browser via the deliciousness known as WebSockets. Vue.js provides the Javascript magic, Bootstrap4 helps tame the interface, and Google Maps provides the mapping capability.

## Getting Started

1. In a terminal: cd find_ip && python3 ./find_ip.py
2. In a browser: 127.0.0.1:8080
3. To quit: control-c until the prompt is returned

### Prerequisites

1. Python 3.6.2+
2. [karellen-sqlite](https://pypi.python.org/pypi/karellen-sqlite)
3. [tornado](http://www.tornadoweb.org/en/stable/)

## How It Works

...insert images...

## Built With

* [Python](https://www.python.org/) - 'nuff said
* [karellen-sqlite](https://pypi.python.org/pypi/karellen-sqlite) - Sqlite extensions
* [tornado](http://tornadoweb.org/en/stable/) - Web Framework
* [VueJs](https://vuejs.org/) - JavaScript Framework 
* [ip-api.com](http://ip-api.com) - IP Geolocation API
* [Google Maps](https://developers.google.com/maps/) - Map API
* [Bootstrap](https://getbootstrap.com/) - UI library

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
