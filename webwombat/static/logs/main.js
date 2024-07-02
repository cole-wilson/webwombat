var app = new Vue({
	el: '#app',
	data: {
		all: [],
		requests: [],
		current_id: "",
		current_request: null,
		searchtext: ""
	},
	methods: {
		clear: function () {
			if (window.confirm('clear logs?')) {
				this.all = [],
				this.requests = [],
				this.current_id = "all"
			}
		},
		updateRequests: function(index, socketid, data) {
			this.$set(this.requests[index], socketid, data)
		},
		formatTime: function(unix) {
			let date = new Date(unix * 1000);
			let str = date.toLocaleString("en-US", {
				year: "numeric",
				month: "2-digit",
				day: "2-digit",
				hour: "2-digit",
				minute: "2-digit",
				second: "2-digit",
				fractionalSecondDigits:3
			})
			return str
		},
		timesort: function(list) {
			return list.sort((a,b)=>a.time-b.time)
		},

		timesortinfo: function(list) {
			return list.sort((a,b)=>a[1].time-b[1].time)
		},
		formatLogLine: function(data) {
			var charts = {
				request: {r:"|b -> p    r|", w:"|b <- p    r|"},
				remote:  {w:"|b    p -> r|", r:"|b    p <- r|"},
			}
			let chart = "|           |"
			console.warn(data.socketid, data.optype)
			if (data.socketid && data.optype)
				chart = charts[data.socketid][data.optype]
			return `${this.formatTime(data.time).padEnd(20)} ${data.level.padEnd(8)} ${(data.requestid||'').padEnd(6)} ${chart} ${data.data}\n`
		}
	}
})

var stuff = {all:[],requests:{}};
let ws = new WebSocket("wss://" + location.host + ":842")

message_indexes = {}
ws.onmessage = (m) => {
	let mdata = JSON.parse(m.data)

	if (mdata.level == "WEBPAGE_INFO") {
		if (!(mdata.requestid in message_indexes)) {
			let newindex = app.requests.push({id:mdata.requestid}) - 1
			message_indexes[mdata.requestid] = newindex
		}
		index = message_indexes[mdata.requestid]
		app.updateRequests(index, mdata.socketid, mdata.data)
	}
	else {
		app.all.push(mdata)
	}
}
