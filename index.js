// Create the WebSocket.
// const means that the identifier can’t be reassigned.
const ws = new WebSocket('ws://127.0.0.1:8080/ws');

function create_websocket_plugin(ws){
	return store => {
		// Called when a message is received from server.
		ws.onmessage = function(event){
			//alert(event.data);
			store.commit('add_host', event.data);
		}
	}
}

const ws_plugin = create_websocket_plugin(ws);

const store = new Vuex.Store({
	state: {
		hosts: []
	},
	plugins: [ws_plugin],
	mutations: {
		add_host(state, host_obj){
			// Add host object to list.
			var host_json = JSON.parse(host_obj);
			// Convert epoch time to local date time.
			var date = new Date(host_json.time_pinged*1000);
			var minutes = date.getMinutes();
			if (minutes < 10) {
				minutes = '0'+minutes;
			}
			host_json.time_pinged = date.getFullYear() + '.' +
									(date.getMonth() + 1) + '.' +
									date.getDate() + ' @ ' +
									date.getHours() + ':' +
									minutes;
			// For Pingable: 0=host online, 1=host offline.
			host_json.status = (host_json.status === '0') ? 'True' : 'False';
			state.hosts.push(host_json);
		}
	}
})

const app = new Vue({
	el: '#app',
	// Provide the store using the "store" option.
	// This will inject the store instance to all child components.
	store,
	// Computed properties re-evaluate when their dependencies change.
	computed: {
		num_hosts(){
			// Count the number of hosts.
			return store.state.hosts.length;
		},
		get_hosts(){
			// Return all hosts.
			return store.state.hosts;
		}
	},
	methods: {
		map_ip(lat,lng){
			// Display IP location on map.
			var lat_lng = {lat:lat,lng:lng};
			var map = new google.maps.Map(document.getElementById('map'), {
				zoom: 8,
				center: lat_lng
			});
			var marker = new google.maps.Marker({
				position: lat_lng,
				map: map
			});
		}
	}
})
