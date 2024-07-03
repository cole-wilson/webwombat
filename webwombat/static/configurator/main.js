Vue.component("list", {props: ['data', 'type', 'placeholder'], template:`
<ul>
	<li v-for="(item, i) in data">
		<input v-model="data[i]" :type="type" :placeholder="placeholder"><button @click="data.splice(i,1)">-</button>
	</li>
	<li><button @click="data.push('')">+ add case</button></li>
</ul>
`});

var app = new Vue({
	el: "main",
	data: {
		rules: [],
		blankrule: {
			type: false,
			name: "",
			match: {method: [], status: [], domain: [], path: [], headers:[]},
			action: {method: null, status: null, domain: null, path: null, headers: [], funcs:[], subs: []}
		},
		rule: false,
		currentrule: null
	},
	methods: {
		addrule: function() {
			if (this.rule.match.domain.length == 0) {alert("you must have at least one match domain"); return;}
			this.rules.push(this.rule);
			this.rule = false;
		},
		newrule: function() {
			this.rule=JSON.parse(JSON.stringify(this.blankrule));this.currentrule=false;
		},
		ruleheader: function(r) {
			var out = r.type + " [";
			if (!r.match.status.includes("*")) out += r.match.status.join(" ") + " ";
			if (!r.match.method.includes("*")) out += r.match.method.join(" ") + " ";
			out += r.match.domain;
			if (!r.match.path.includes("*")) out += " " + r.match.path.join(" ");
			out += "] -> ";

			if (r.action.funcs.length > 0) {
				out += r.action.funcs.join(" ");
			} else {
				out += "["
				if ('status' in r.action) out += r.action.status + " ";
				if ('method' in r.action) out += r.action.method + " ";
				if ('domain' in r.action) out += r.action.domain + "";
				if ('path' in r.action) out += " " + r.action.path + "";
				out += "]"
			}
			return out;

		}
	}
});


window.onload = async function() {
	let data = await (await fetch("/rules.json")).json();
	console.log("got rules:", data);
	for (i in data) {
		data[i].type = data[i].match.type[0];
		data[i].match.headers = Object.keys(data[i].match.headers).map(k=>`${k}: ${data[i].match.headers[k]}`)
		data[i].action.headers = Object.keys(data[i].action.headers).map(k=>`${k}: ${data[i].action.headers[k]}`)
		data[i].action.funcs = data[i].action.funcs.map(f=>`@${f.modulestr}:${f.attrstr} ${f.args.join(' ')}`.replace("webwombat.transformers:",""))

	}
	console.log("parsed rules:", data);
	app.rules = data;
}


function format() {
	for (rulei in app.rules) {
		let rule = app.rules[rulei]
		console.log(rule)
	}
}
