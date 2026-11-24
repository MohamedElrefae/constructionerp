const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");

class MiniElement {
	constructor(tagName, attributes = {}) {
		this.tagName = tagName.toUpperCase();
		this.attributes = { ...attributes };
		this.children = [];
		this.parentNode = null;
		this.handlers = Object.create(null);
		this.style = {};
		this.textContent = "";
		this.disabled = false;
		this.selected = Object.prototype.hasOwnProperty.call(attributes, "selected");
		this.ownerDocument = null;
	}

	getAttribute(name) {
		return Object.prototype.hasOwnProperty.call(this.attributes, name)
			? this.attributes[name]
			: null;
	}

	setAttribute(name, value) {
		this.attributes[name] = String(value);
		if (name === "selected") this.selected = true;
	}

	hasClass(className) {
		return (this.getAttribute("class") || "").split(/\s+/).includes(className);
	}

	appendChild(child) {
		child.parentNode = this;
		const bindDocument = (node) => {
			node.ownerDocument = this.ownerDocument;
			node.children.forEach(bindDocument);
		};
		bindDocument(child);
		this.children.push(child);
		return child;
	}

	focus() {
		this.ownerDocument.activeElement = this;
		this.trigger("focus");
	}

	trigger(eventName) {
		if (eventName === "focus" && this.ownerDocument) this.ownerDocument.activeElement = this;
		const event = {
			target: this,
			currentTarget: this,
			preventDefault() {},
			stopPropagation() {},
		};
		(this.handlers[eventName] || []).forEach((handler) => handler.call(this, event));
	}

	getBoundingClientRect() {
		return { top: 100, bottom: 132, left: 20, width: 180 };
	}

	matches(selector) {
		if (selector === ":visible") {
			return this.style.display !== "none" && !this.hidden;
		}
		if (selector === ":selected") return this.selected;

		let baseSelector = selector;
		let pseudo = null;
		const pseudoMatch = selector.match(/:(visible|selected)$/);
		if (pseudoMatch) {
			pseudo = pseudoMatch[1];
			baseSelector = selector.slice(0, -pseudoMatch[0].length);
		}

		const tagMatch = baseSelector.match(/^[a-zA-Z][\w-]*/);
		if (tagMatch && this.tagName !== tagMatch[0].toUpperCase()) return false;

		const classes = [...baseSelector.matchAll(/\.([\w-]+)/g)].map((match) => match[1]);
		if (classes.some((className) => !this.hasClass(className))) return false;

		const attributes = [...baseSelector.matchAll(/\[([\w-]+)(?:=['"]?([^'"]*)['"]?)?\]/g)];
		if (
			attributes.some((match) => {
				const actual = this.getAttribute(match[1]);
				return match[2] === undefined ? actual === null : actual !== match[2];
			})
		) {
			return false;
		}

		if (pseudo === "visible") return this.style.display !== "none" && !this.hidden;
		if (pseudo === "selected") return this.selected;
		return true;
	}

	descendants() {
		return this.children.flatMap((child) => [child, ...child.descendants()]);
	}
}

class MiniQuery {
	constructor(nodes) {
		this.nodes = nodes;
		this.length = nodes.length;
		this[0] = nodes[0];
	}

	on(eventNames, handler) {
		eventNames.split(/\s+/).forEach((eventName) => {
			this.nodes.forEach((node) => {
				(node.handlers[eventName] ||= []).push(handler);
			});
		});
		return this;
	}

	trigger(eventName) {
		this.nodes.forEach((node) => node.trigger(eventName));
		return this;
	}

	each(callback) {
		this.nodes.forEach((node, index) => callback.call(node, index, node));
		return this;
	}

	find(selector) {
		return new MiniQuery(this.nodes.flatMap((node) => node.descendants().filter((el) => el.matches(selector))));
	}

	closest(selector) {
		for (const node of this.nodes) {
			let current = node;
			while (current) {
				if (current.matches(selector)) return new MiniQuery([current]);
				current = current.parentNode;
			}
		}
		return new MiniQuery([]);
	}

	parent() {
		return new MiniQuery(this.nodes.map((node) => node.parentNode).filter(Boolean));
	}

	append(content) {
		const incoming = content instanceof MiniQuery ? content.nodes : parseHTML(content);
		incoming.forEach((node) => {
			this.nodes.forEach((parent) => parent.appendChild(node));
		});
		return this;
	}

	css(styles, value) {
		if (typeof styles === "string") {
			this.nodes.forEach((node) => {
				node.style[styles] = value;
			});
			return this;
		}
		this.nodes.forEach((node) => Object.assign(node.style, styles));
		return this;
	}

	hide() {
		return this.css({ display: "none" });
	}

	is(selector) {
		return this.nodes.some((node) => node.matches(selector));
	}

	hasClass(className) {
		return this.nodes.some((node) => node.hasClass(className));
	}

	attr(name, value) {
		if (value === undefined) return this.nodes[0]?.getAttribute(name) ?? null;
		this.nodes.forEach((node) => node.setAttribute(name, value));
		return this;
	}

	prop(name, value) {
		if (value === undefined) return this.nodes[0]?.[name];
		this.nodes.forEach((node) => {
			node[name] = value;
		});
		return this;
	}

	val(value) {
		if (value === undefined) {
			const selected = this.nodes[0]?.descendants().find((node) => node.tagName === "OPTION" && node.selected);
			return selected?.getAttribute("value") ?? "";
		}
		this.nodes.forEach((node) => {
			node.descendants()
				.filter((candidate) => candidate.tagName === "OPTION")
				.forEach((option) => {
					option.selected = option.getAttribute("value") === value;
				});
		});
		return this;
	}

	text(value) {
		if (value === undefined) return this.nodes[0]?.textContent.trim() ?? "";
		this.nodes.forEach((node) => {
			node.textContent = value;
		});
		return this;
	}

	empty() {
		this.nodes.forEach((node) => {
			node.children = [];
		});
		return this;
	}

	first() {
		return new MiniQuery(this.nodes.slice(0, 1));
	}

	focus() {
		this.nodes.forEach((node) => node.focus());
		return this;
	}

	ready(handler) {
		handler();
		return this;
	}
}

function parseHTML(html) {
	const roots = [];
	const stack = [];
	const tokenPattern = /<\/?([a-zA-Z][\w-]*)([^>]*)>|([^<]+)/g;
	let match;
	while ((match = tokenPattern.exec(html))) {
		if (match[3]) {
			if (stack.length) stack[stack.length - 1].textContent += match[3];
			continue;
		}
		const closing = match[0].startsWith("</");
		const tagName = match[1].toLowerCase();
		if (closing) {
			stack.pop();
			continue;
		}
		const attributes = {};
		const attributePattern = /([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
		let attribute;
		while ((attribute = attributePattern.exec(match[2]))) {
			attributes[attribute[1]] = attribute[2] ?? attribute[3] ?? attribute[4] ?? "";
		}
		const element = new MiniElement(tagName, attributes);
		if (stack.length) stack[stack.length - 1].appendChild(element);
		else roots.push(element);
		if (!match[0].endsWith("/>") && !["input", "br", "img", "hr", "meta", "link"].includes(tagName)) {
			stack.push(element);
		}
	}
	return roots;
}

function allElements(document) {
	return [document.body, ...document.body.descendants(), ...document.head.descendants()];
}

function buildSelectHarness() {
	const document = {
		activeElement: null,
		handlers: Object.create(null),
		body: new MiniElement("body"),
		head: new MiniElement("head"),
		getElementById(id) {
			return allElements(document).find((element) => element.getAttribute("id") === id) || null;
		},
		createElement(tagName) {
			return new MiniElement(tagName);
		},
	};
	allElements(document).forEach((element) => {
		element.ownerDocument = document;
	});

	const controlWrapper = new MiniElement("div", {
		class: "frappe-control",
		"data-fieldtype": "Select",
		"data-fieldname": "naming_series",
	});
	const selectWrapper = new MiniElement("div", { class: "control-select-wrapper" });
	const select = new MiniElement("select", { class: "form-control", name: "naming_series" });
	select.appendChild(new MiniElement("option", { value: "RPH-.YYYY.-", selected: "" }));
	select.appendChild(new MiniElement("option", { value: "ALT-.YYYY.-" }));
	selectWrapper.appendChild(select);
	controlWrapper.appendChild(selectWrapper);
	document.body.appendChild(controlWrapper);

	const field = {
		df: { fieldtype: "Select", fieldname: "naming_series", label: "Series" },
	};
	controlWrapper.fieldobj = field;

	const context = {
		console,
		document,
		window: { innerHeight: 900 },
		setTimeout: (handler) => {
			handler();
			return 0;
		},
		clearTimeout() {},
		MutationObserver: class {
			observe() {}
			disconnect() {}
		},
		__: (message) => message,
		frappe: {
			provide(name) {
				let target = context;
				name.split(".").forEach((part) => {
					target[part] ||= {};
					target = target[part];
				});
			},
			utils: {
				escape_html: (value) =>
					String(value).replace(/[&<>"']/g, (character) => ({
						"&": "&amp;",
						"<": "&lt;",
						">": "&gt;",
						'"': "&quot;",
						"'": "&#39;",
					})[character]),
			},
		},
	};

	function $(input) {
		if (input instanceof MiniElement) return new MiniQuery([input]);
		if (input === document) return new MiniQuery([document]);
		if (typeof input === "string") {
			const selector = input.trim();
			if (selector.startsWith("<")) return new MiniQuery(parseHTML(selector));
			const parts = selector.split(/\s+/);
			return new MiniQuery(
				allElements(document).filter((element) => {
					if (!element.matches(parts[parts.length - 1])) return false;
					let ancestor = element.parentNode;
					for (let index = parts.length - 2; index >= 0; index -= 1) {
						while (ancestor && !ancestor.matches(parts[index])) ancestor = ancestor.parentNode;
						if (!ancestor) return false;
						ancestor = ancestor.parentNode;
					}
					return true;
				})
			);
		}
		if (input instanceof MiniQuery) return input;
		return new MiniQuery([]);
	}

	context.$ = $;
	vm.runInNewContext(
		fs.readFileSync(path.join(root, "construction/public/js/overrides/ct_select_control.js"), "utf8"),
		context,
		{ filename: "construction/public/js/overrides/ct_select_control.js" }
	);

	const dropdown = $(".ct-unified-dropdown");
	// Bootstrap's stylesheet keeps .dropdown-menu hidden until it is opened.
	dropdown.find(".ct-dropdown-menu").css({ display: "none" });
	return {
		document,
		select: new MiniQuery([select]),
		button: dropdown.find(".ct-dropdown-btn"),
		menu: dropdown.find(".ct-dropdown-menu"),
		list: dropdown.find(".ct-dropdown-list"),
	};
}

test("Frappe automatic first-field focus does not open the themed Select menu", () => {
	const harness = buildSelectHarness();

	// form.js::focus_on_first_input triggers focus on the first visible input.
	harness.select.trigger("focus");

	assert.equal(harness.menu.is(":visible"), false, "automatic focus must not open the menu");
	assert.equal(harness.select.attr("tabindex"), "-1", "the hidden select must stay out of tab order");
	assert.equal(
		harness.document.activeElement,
		harness.button[0],
		"keyboard focus must move to the visible dropdown button"
	);
});

test("the themed Select menu opens when its visible button is activated", () => {
	const harness = buildSelectHarness();

	harness.button.trigger("click");

	assert.equal(harness.menu.is(":visible"), true);
	assert.equal(harness.list.find(".dropdown-item").length, 2);

	harness.button.trigger("click");
	assert.equal(harness.menu.is(":visible"), false);
});
