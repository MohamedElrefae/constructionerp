const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup() {
  const elements = new Map();
  function el() {
    return {
      handlers: {}, found: {}, textValue: '', htmlValue: '',
      on(events, selector, fn) { if (!fn) fn = selector; for (const e of events.split(' ')) (this.handlers[e] ||= []).push(fn); return this; },
      off(events) { for (const e of events.split(' ')) delete this.handlers[e]; return this; },
      trigger(event, arg) { for (const [name, handlers] of Object.entries(this.handlers)) if (name.split('.')[0] === event) handlers.forEach(h => h({}, arg)); return this; },
      ready(fn) { fn(); return this; },
      find(s) { return this.found[s] ||= el(); }, append(s) { this.htmlValue += s; return this; },
      html(s) { if (s === undefined) return this.htmlValue; this.htmlValue = s; return this; },
      text(s) { if (s === undefined) return this.textValue; this.textValue = s; return this; },
      empty() { this.htmlValue = ''; this.textValue = ''; return this; },
      removeClass() { return this; }, addClass() { return this; }, toggleClass() { return this; },
    };
  }
  const document = el(), root = el(), wrapper = el();
  const storage = new Map();
  const localStorage = {getItem: k => storage.get(k) || null, setItem: (k,v) => storage.set(k,v), removeItem: k => storage.delete(k)};
  const requests = [];
  const win = Object.assign(el(), { location: {origin: 'http://lab', search: ''} });
  const frappe = {
    boot: {scope_context_enabled: true, scope_context: {current: {company:'C'}, hierarchy: {companies:[{name:'C'}], projects:[{name:'A',company:'C'}, {name:'B',company:'C'}, {name:'D',company:'C'}]}}},
    pages: {'execution-breakdown': {}}, ui: {make_app_page: () => ({main: root})},
    call: (opts) => {
      if (frappe.throwNextTree && opts.method.endsWith(".get_tree")) {
        frappe.throwNextTree = false;
        throw new Error("synchronous request failure");
      }
      let resolve, reject;
      const p = new Promise((a,b) => {resolve=a;reject=b});
      const record = {opts,resolve,reject};
      function jqueryPromise(promise) {
        const jq = {
          then: (ok, err) => jqueryPromise(promise.then(ok, err)),
          fail: (fn) => { record.fail = fn; return jq; },
          always: (fn) => jqueryPromise(promise.finally(fn)),
        };
        return jq;
      }
      const jq = jqueryPromise(p);
      record.jqueryPromise = jq;
      requests.push(record);
      return jq;
    },
    utils: {escape_html: String, icon: () => "", is_rtl: () => false}, prompt(){}, confirm(){},
  };
  function $(arg) { return arg; }
  const context = vm.createContext({window:win, document, localStorage, frappe, $, __: x => x, console, setTimeout});
  vm.runInContext(fs.readFileSync('construction/public/js/scope_context.js','utf8'), context);
  vm.runInContext(fs.readFileSync('construction/construction/page/execution_breakdown/execution_breakdown.js','utf8'), context);
  frappe.pages['execution-breakdown'].on_page_load(wrapper);
  return {win, document, root, wrapper, requests, storage, frappe};
}
const tick = () => new Promise(resolve => setImmediate(resolve));
function confirm(request, version = 1) { request.opts.callback({message:{success:true,scope_version:version,current_scope:{company:request.opts.args.company,cost_center:request.opts.args.cost_center,project:request.opts.args.project,department:request.opts.args.department}}}); }
function tree(request, project, label) { request.resolve({message:{project,company:'C',actions:{},nodes:[{name:label,title:label,ebs_code:'EBS-1'}]}}); }

test('topbar saves serialize, fail closed, prevent stale trees, and detach on exit', async () => {
  const {win,document,root,wrapper,requests} = setup();
  const scope = win.scopeContext, body = root.find('[data-role="tree"]');
  assert.match(root.find('[data-role="status"]').textValue, /Select a Project/);
  scope.setProject('A');
  assert.equal(requests.length,1); assert.equal(body.htmlValue,'');
  scope.setProject('B');
  assert.equal(requests.length,1, 'second save waits for first completion');
  confirm(requests[0]);
  assert.equal(requests.length,2); assert.equal(requests[1].opts.args.project,'B');
  assert.equal(body.htmlValue,'');
  requests[1].opts.error();
  assert.match(root.find('[data-role="status"]').textValue,/Could not confirm/);
  assert.equal(requests.length,2, 'failed save must not load a tree');
  scope.setProject('D'); assert.equal(requests.length,3); confirm(requests[2],3);
  assert.equal(requests.length,4); assert.equal(requests[3].opts.args.project,'D');
  scope.setProject('A'); assert.equal(body.htmlValue,'');
  tree(requests[3], 'D', 'OLD'); await tick(); assert.doesNotMatch(body.htmlValue,/OLD/);
  confirm(requests[4],4); assert.equal(requests[5].opts.args.project,'A');
  tree(requests[5], 'A', 'CURRENT'); await tick(); assert.match(body.htmlValue,/CURRENT/);
  wrapper.trigger('hide'); assert.equal(body.htmlValue,'');
  assert.equal(document.handlers['scope:changed.executionBreakdown'],undefined);
  wrapper.trigger('show'); assert.equal(requests[6].opts.args.project,'A');
});

test('server-normalized scope mismatch remains unconfirmed', () => {
  const {win,requests,root} = setup();
  win.scopeContext.setProject('A');
  requests[0].opts.callback({message:{success:true,scope_version:1,current_scope:{company:'C',project:null}}});
  assert.equal(win.scopeContext._saveFailed,true);
  assert.equal(requests.length,1);
  assert.match(root.find('[data-role="status"]').textValue,/Could not confirm/);
});

test('a failed old save drains the newer selection without exposing the failed scope', () => {
  const {win,requests,root} = setup();
  win.scopeContext.setProject('A');
  win.scopeContext.setProject('B');
  requests[0].opts.error();
  assert.equal(requests.length,2);
  assert.equal(requests[1].opts.args.project,'B');
  assert.equal(root.find('[data-role="tree"]').htmlValue,'');
  confirm(requests[1],2);
  assert.equal(requests[2].opts.args.project,'B');
});

test('cross-tab changes are unconfirmed and failed save can be retried', () => {
  const {win,requests,root} = setup();
  win.scopeContext.setProject('A'); requests[0].opts.error();
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  assert.equal(requests.length,2);
  assert.equal(requests[1].opts.method, 'construction.api.scope_context_api.get_scope_context');
  requests[1].opts.callback({message: {scope: {company:'C', cost_center:null, project:'A', department:null}, scope_version:1}});
  assert.equal(requests.length,3); confirm(requests[2]);
  assert.equal(requests.length,4);
  win.scopeContext._loadFromLocalStorage();
  win.scopeContext._emitChange();
  assert.equal(win.scopeContext._saveFailed,true);
  assert.equal(root.find('[data-role="tree"]').htmlValue,'');
});


test('external tab change discards stale queued save and invalidates in-flight success', () => {
  const {win,requests,root,storage} = setup();
  const scope = win.scopeContext;
  scope.setProject('A');
  scope.setProject('B');
  assert.equal(requests.length,1);
  storage.set('scope_context_current', JSON.stringify({site:'http://lab',company:'C',project:'D'}));
  win.handlers['storage.scopeContext'][0]({originalEvent:{key:'scope_context_current'}});
  assert.equal(scope.current.project,'D');
  assert.equal(scope._saveQueued,null);
  assert.equal(scope._saveFailed,true);
  confirm(requests[0]);
  assert.equal(requests.length,1, 'stale B must never be submitted');
  assert.equal(scope._saveFailed,true);
  assert.equal(root.find('[data-role="tree"]').htmlValue,'');
  assert.match(root.find('[data-role="status"]').textValue,/Could not confirm/);
});

test('external change invalidates in-flight failure and allows explicit retry after it settles', () => {
  const {win,requests,root,storage} = setup();
  const scope = win.scopeContext;
  scope.setProject('A'); scope.setProject('B');
  storage.set('scope_context_current', JSON.stringify({site:'http://lab',company:'C',project:'D'}));
  win.handlers['storage.scopeContext'][0]({originalEvent:{key:'scope_context_current'}});
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  assert.equal(requests.length,1, 'retry cannot start while old save remains in flight');
  requests[0].opts.error();
  assert.equal(requests.length,1, 'failed old request must not send stale queued B');
  assert.equal(scope._saveFailed,true);
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  assert.equal(requests.length,2);
  assert.equal(requests[1].opts.method, 'construction.api.scope_context_api.get_scope_context');
  requests[1].opts.callback({message: {scope: {company:'C', cost_center:null, project:'D', department:null}, scope_version:2}});
  assert.equal(requests.length,3);
  assert.equal(requests[2].opts.args.project,'D');
  confirm(requests[2],2);
  assert.equal(requests[3].opts.args.project,'D');
});

test('two tabs with same starting version reject the late stale save in a versioned server model', () => {
  const first = setup(), second = setup();
  const server = {version:0, project:null};
  function commit(request) {
    if (request.opts.args.expected_scope_version !== server.version) { request.opts.error(); return; }
    server.version++;
    server.project = request.opts.args.project;
    confirm(request, server.version);
  }
  first.win.scopeContext.setProject('A');
  second.win.scopeContext.setProject('D');
  commit(second.requests[0]);
  assert.equal(server.project,'D');
  first.storage.set('scope_context_current', JSON.stringify({site:'http://lab',company:'C',project:'D',version:1}));
  first.win.handlers['storage.scopeContext'][0]({originalEvent:{key:'scope_context_current'}});
  commit(first.requests[0]);
  assert.equal(server.project,'D');
  assert.equal(first.win.scopeContext._saveFailed,true);
  assert.equal(first.root.find('[data-role="tree"]').htmlValue,'');
  assert.equal(second.requests[1].opts.args.project,'D');
});


test('internally handled Frappe error still marks scope unconfirmed', () => {
  const {win,requests,root} = setup();
  win.scopeContext.setProject('A');
  requests[0].fail();
  assert.equal(win.scopeContext._savePending,false);
  assert.equal(win.scopeContext._saveFailed,true);
  assert.match(root.find('[data-role="status"]').textValue,/Could not confirm/);
  requests[0].opts.error();
  assert.equal(win.scopeContext._saveFailed,true, 'duplicate error handlers settle once');
});

test('retry refreshes authoritative scope and resends the user intent when unchanged', () => {
  const {win,root,requests} = setup();
  const scope = win.scopeContext;
  scope.setProject('A');
  requests[0].opts.error();
  assert.equal(scope._saveFailed, true);
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  assert.equal(requests.length, 2);
  assert.equal(requests[1].opts.method, 'construction.api.scope_context_api.get_scope_context');
  requests[1].opts.callback({message: {scope: {company:'C', cost_center:null, project:'A', department:null}, scope_version:4}});
  assert.equal(requests.length, 3);
  assert.equal(requests[2].opts.args.project, 'A');
  assert.equal(requests[2].opts.args.expected_scope_version, 4);
  confirm(requests[2], 5);
  assert.equal(requests.length, 4);
  assert.equal(requests[3].opts.args.project, 'A', 'tree loads for the confirmed scope');
  assert.equal(scope._saveFailed, false);
  assert.equal(scope._attemptedScope, null);
});

test('retry marks the conflict: it neither overwrites nor silently changes the Project', () => {
  const {win,root,requests} = setup();
  const scope = win.scopeContext;
  scope.setProject('A');
  requests[0].opts.error();
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  requests[1].opts.callback({message: {scope: {company:'C', cost_center:null, project:'B', department:null}, scope_version:3}});
  assert.equal(scope.current.project, 'A', 'local selection untouched');
  assert.equal(scope._version, 3);
  assert.equal(scope._conflict.authoritative.project, 'B');
  assert.equal(requests.length, 2, 'no re-save while the conflict needs resolution');
  assert.equal(scope._saveFailed, true);
  assert.equal(root.find('[data-role="tree"]').htmlValue, '');
  assert.match(root.find('[data-role="conflict-message"]').textValue, /B/);
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  assert.equal(requests.length, 2, 'repeating retry stays blocked while the conflict panel is up');
});

test('conflict panel: apply my selection re-saves the user intent with the fresh version', () => {
  const {win,root,requests} = setup();
  const scope = win.scopeContext;
  scope.setProject('A');
  requests[0].opts.error();
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  requests[1].opts.callback({message: {scope: {company:'C', cost_center:null, project:'B', department:null}, scope_version:9}});
  assert.equal(scope._conflict.authoritative.project, 'B');
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'apply-selection' : null});
  assert.equal(requests.length, 3);
  assert.equal(requests[2].opts.args.project, 'A');
  assert.equal(requests[2].opts.args.expected_scope_version, 9);
  confirm(requests[2], 10);
  assert.equal(requests.length, 4);
  assert.equal(requests[3].opts.args.project, 'A', 'tree loads for the user intent');
  assert.equal(scope._conflict, null);
  assert.equal(scope._saveFailed, false);
  assert.equal(root.find('[data-role="conflict-message"]').textValue, '');
});

test('conflict panel: use saved scope adopts the authoritative Project without saving', () => {
  const {win,root,requests} = setup();
  const scope = win.scopeContext;
  scope.setProject('A');
  requests[0].opts.error();
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  requests[1].opts.callback({message: {scope: {company:'C', cost_center:null, project:'B', department:null}, scope_version:9}});
  assert.equal(scope._conflict.authoritative.project, 'B');
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'use-saved' : null});
  assert.equal(scope.current.project, 'B');
  assert.equal(scope._version, 9);
  assert.equal(scope._conflict, null);
  assert.equal(scope._saveFailed, false);
  assert.equal(requests.length, 3);
  assert.equal(requests[2].opts.args.project, 'B', 'tree loads for the adopted saved scope');
  assert.equal(root.find('[data-role="conflict-message"]').textValue, '');
});

test('stale conflict clears when the user selects a new Project and its save succeeds', () => {
  const {win,root,requests} = setup();
  const scope = win.scopeContext;
  scope.setProject('A');
  requests[0].opts.error();
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  requests[1].opts.callback({message: {scope: {company:'C', cost_center:null, project:'B', department:null}, scope_version:9}});
  assert.equal(scope._conflict.authoritative.project, 'B');
  assert.match(root.find('[data-role="conflict-message"]').textValue, /B/);
  // User selects D in the top bar; its save succeeds while the panel is up.
  scope.setProject('D');
  assert.equal(scope._conflict, null, 'a new selection supersedes the stale conflict');
  assert.equal(root.find('[data-role="conflict-message"]').textValue, '', 'panel message cleared');
  assert.equal(requests.length, 3, 'the new selection save starts');
  confirm(requests[2], 10);
  assert.equal(requests.length, 4);
  assert.equal(requests[3].opts.args.project, 'D', 'tree loads for the newly saved Project');
  assert.equal(scope.current.project, 'D');
  scope.applySavedScope();
  assert.equal(scope.current.project, 'D', 'stale Use-saved cannot switch back to the obsolete Project');
});

test('retry response is discarded when a newer selection saves first', () => {
  const {win,root,requests} = setup();
  const scope = win.scopeContext;
  scope.setProject('A');
  requests[0].opts.error();
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'retry-scope' : null});
  assert.equal(requests[1].opts.method, 'construction.api.scope_context_api.get_scope_context');
  // User selects D; its save starts and succeeds while the read is in flight.
  scope.setProject('D');
  assert.equal(requests.length, 3);
  assert.equal(requests[2].opts.args.project, 'D');
  confirm(requests[2], 7);
  assert.equal(scope._conflict, null);
  assert.equal(scope.current.project, 'D');
  // The late retry response for the older read arrives: must be discarded.
  requests[1].opts.callback({message: {scope: {company:'C', cost_center:null, project:'B', department:null}, scope_version:3}});
  assert.equal(scope._conflict, null, 'late retry must not reopen the obsolete conflict');
  assert.equal(scope._version, 7, 'late retry must not replace the current version');
  assert.equal(scope.current.project, 'D');
});


test('jQuery-style requests without finally handle success and failure and release action lock', async () => {
  const {win,requests,root} = setup();
  win.scopeContext.setProject('A'); confirm(requests[0]);
  assert.equal(typeof requests[1].jqueryPromise.finally, 'undefined');
  assert.equal(typeof requests[1].jqueryPromise.then, 'function');
  tree(requests[1], 'A', 'FIRST'); await tick();
  assert.match(root.find('[data-role="tree"]').htmlValue,/FIRST/);
  win.scopeContext.setProject('B'); confirm(requests[2],2);
  requests[3].reject(new Error('denied')); await tick();
  assert.match(root.find('[data-role="status"]').textValue,/Not permitted/);
  win.scopeContext.setProject('A'); confirm(requests[4],3);
  tree(requests[5], 'A', 'AFTER'); await tick();
  assert.match(root.find('[data-role="tree"]').htmlValue,/AFTER/);
});


test('synchronous request failure clears in-flight state for later actions', async () => {
  const {win,requests,root,frappe} = setup();
  win.scopeContext.setProject('A');
  frappe.throwNextTree = true;
  confirm(requests[0]); await tick();
  assert.match(root.find('[data-role="status"]').textValue,/Not permitted/);
  win.scopeContext.setProject('B'); confirm(requests[1],2);
  tree(requests[2], 'B', 'NODE'); await tick();
  const before = requests.length;
  root.handlers.click[0].call({attr: key => key === 'data-action' ? 'toggle' : 'NODE'});
  assert.equal(requests.length, before + 1, 'in-flight lock must be released');
  assert.match(requests[3].opts.method,/set_disabled$/);
});

test('tree renders hierarchical positions, expands and collapses, and retains stable API identifiers', async () => {
  const {win, requests, root} = setup();
  win.scopeContext.setProject('A'); confirm(requests[0]);
  const nodes = [
    {name:'R1', title:'Building', is_group:1, parent_node:null, ebs_code:'EBS-0001'},
    {name:'C1', title:'Floor', is_group:1, parent_node:'R1', ebs_code:'EBS-0002'},
    {name:'G1', title:'Zone', is_group:0, parent_node:'C1', ebs_code:'EBS-0003'},
    {name:'C2', title:'Roof', is_group:0, parent_node:'R1', ebs_code:'EBS-0004'},
    {name:'R2', title:'External', is_group:0, parent_node:null, ebs_code:'EBS-0005'},
  ];
  requests[1].resolve({message:{project:'A', company:'C', actions:{}, nodes}}); await tick();
  const body = root.find('[data-role="tree"]');
  for (const [number, title] of [['1','Building'],['1.1','Floor'],['1.1.1','Zone'],['1.2','Roof'],['2','External']]) {
    assert.ok(body.htmlValue.includes('>' + number + ' ' + title + '<'), `missing position ${number}`);
  }
  assert.match(body.htmlValue, /class="tree-children"/);
  assert.match(body.htmlValue, /node-parent/);
  assert.match(body.htmlValue, /aria-expanded="true"/);
  assert.equal(root.find('[data-role="company"]').textValue, "");
  root.handlers.click[0].call({attr:key => key === 'data-action' ? 'expand' : 'R1'});
  assert.match(body.htmlValue, /aria-expanded="false"/);
  // Company label is removed by the new rendering.
  assert.equal(root.find('[data-role="company"]').textValue, "");
  assert.doesNotMatch(body.htmlValue, />1\.1 Floor<\/a>/);
  assert.match(body.htmlValue, />2 External<\/a>/);
  root.handlers.click[0].call({attr:key => key === 'data-action' ? 'expand' : 'R1'});
  assert.match(body.htmlValue, />1\.1\.1 Zone<\/a>/);
  assert.deepEqual(nodes.map(n => n.ebs_code), ['EBS-0001','EBS-0002','EBS-0003','EBS-0004','EBS-0005']);
});

test('tree positions are recalculated from current parent links after a refresh', async () => {
  const {win, document, requests, root} = setup();
  win.scopeContext.setProject('A'); confirm(requests[0]);
  const rootNode = {name:'R', title:'Root', is_group:1, parent_node:null, ebs_code:'EBS-0001'};
  const group = {name:'G', title:'Group', is_group:1, parent_node:'R', ebs_code:'EBS-0002'};
  const item = {name:'I', title:'Item', is_group:0, parent_node:'R', ebs_code:'EBS-0003'};
  requests[1].resolve({message:{project:'A', actions:{}, nodes:[rootNode, group, item]}}); await tick();
  const body = root.find('[data-role="tree"]');
  assert.ok(body.htmlValue.includes('>1.2 Item<'));
  document.trigger('scope:save_confirmed');
  requests[2].resolve({message:{project:'A', actions:{}, nodes:[rootNode, group, {...item, parent_node:'G'}]}}); await tick();
  assert.ok(body.htmlValue.includes('>1.1.1 Item<'));
  assert.equal(item.ebs_code, 'EBS-0003', 'display position must not rewrite the stable identifier');
});

test('large execution tree has a single tab stop', async () => {
  const {win, root, requests} = setup();
  win.scopeContext.setProject('A');
  confirm(requests[0]);
  const nodes = Array.from({length: 10000}, (_, i) => ({name: `N${i}`, title: `Node ${i}`, parent_node: null}));
  requests[1].resolve({message: {project: 'A', company: 'C', actions: {}, nodes}});
  await tick();
  const html = root.find('[data-role="tree"]').htmlValue;
  assert.equal((html.match(/role="treeitem"/g) || []).length, 10000);
  assert.equal((html.match(/tabindex="0"/g) || []).length, 1);
  assert.equal((html.match(/tabindex="-1"/g) || []).length, 9999);
});

test('nested tree click and keydown toggle only the target node without bubbling to ancestors', async () => {
  function parseHtml(html) {
    const rootNode = { tag: 'div', attrs: {}, children: [], parent: null };
    const stack = [rootNode];
    const re = /<(\/?)([a-z0-9]+)([^>]*)>/gi;
    let m;
    while ((m = re.exec(html))) {
      const [, close, tag, attrStr] = m;
      if (close) {
        if (stack.length > 1) stack.pop();
      } else {
        const attrs = {};
        const are = /([a-z0-9-]+)=(["'])(.*?)\2/gi;
        let am;
        while ((am = are.exec(attrStr))) attrs[am[1]] = am[3];
        const node = { tag: tag.toLowerCase(), attrs, children: [], parent: stack[stack.length - 1] };
        stack[stack.length - 1].children.push(node);
        if (!attrStr.trim().endsWith('/')) stack.push(node);
      }
    }
    return rootNode;
  }
  function matchesSelector(el, sel) {
    if (!el || !el.attrs) return false;
    if (sel === "[role='treeitem']" || sel === '[role="treeitem"]') return el.attrs.role === 'treeitem';
    if (sel === '[data-action]') return 'data-action' in el.attrs;
    if (sel === '.tree-children') return (el.attrs.class || '').split(/\s+/).includes('tree-children');
    return false;
  }
  function collectMatches(rootNode, sel, out = []) {
    for (const c of rootNode.children || []) {
      if (matchesSelector(c, sel)) out.push(c);
      collectMatches(c, sel, out);
    }
    return out;
  }
  function findFirst(rootNode, pred) {
    if (pred(rootNode)) return rootNode;
    for (const c of rootNode.children || []) {
      const hit = findFirst(c, pred);
      if (hit) return hit;
    }
    return null;
  }

  let focusedName = null;
  let focusedAction = null;
  function wrapDom(el) {
    return {
      0: el,
      length: el ? 1 : 0,
      _isDom: true,
      attr(k) { return el && el.attrs ? el.attrs[k] : undefined; },
      closest(sel) {
        for (let cur = el; cur; cur = cur.parent) {
          if (matchesSelector(cur, sel)) return wrapDom(cur);
        }
        return { length: 0 };
      },
    };
  }
  function wrapDomList(list) {
    return {
      length: list.length,
      attr(key, value) {
        if (value === undefined) return list[0] && list[0].attrs[key];
        list.forEach((item) => { item.attrs[key] = value; });
        return this;
      },
      filter(fn) {
        return wrapDomList(list.filter((item) => fn.call(item)));
      },
      trigger(ev) {
        if (ev === 'focus' && list[0] && list[0].attrs) {
          focusedName = list[0].attrs['data-name'] || null;
          focusedAction = list[0].attrs['data-action'] || null;
          document.activeElement = { treeOwned: true, tagName: list[0].tag.toUpperCase(), getAttribute: key => list[0].attrs[key] };
        }
        return this;
      },
    };
  }
  function makeEl() {
    return {
      handlers: {}, delegated: [], found: {}, textValue: '', htmlValue: '',
      on(events, selector, fn) {
        if (typeof selector === 'function') {
          fn = selector;
          selector = null;
        }
        for (const e of events.split(' ')) {
          const ev = e.split('.')[0];
          if (selector) this.delegated.push({ ev, selector, fn });
          else (this.handlers[e] ||= []).push(fn);
        }
        return this;
      },
      off(events) { for (const e of events.split(' ')) delete this.handlers[e]; return this; },
      trigger(event, arg) {
        if (event === 'focus' && this[0]) document.activeElement = this[0];
        for (const [name, handlers] of Object.entries(this.handlers)) {
          if (name.split('.')[0] === event) handlers.forEach((h) => h({}, arg));
        }
        return this;
      },
      ready(fn) { fn(); return this; },
      find(s) {
        if (s === '[role="treeitem"]' || s === "[role='treeitem']" || s === '[data-action]') {
          return wrapDomList(collectMatches(parseHtml(this.htmlValue || ''), s));
        }
        return this.found[s] ||= makeEl();
      },
      append(s) { this.htmlValue += s; return this; },
      attr(key, value) { this.attrs ||= {}; if (value === undefined) return this.attrs[key]; this.attrs[key] = value; return this; },
      html(s) { if (s === undefined) return this.htmlValue; this.htmlValue = s; return this; },
      text(s) { if (s === undefined) return this.textValue; this.textValue = s; return this; },
      empty() { this.htmlValue = ''; this.textValue = ''; return this; },
      removeClass() { return this; }, addClass() { return this; }, toggleClass() { return this; },
    };
  }

  const document = makeEl(), root = makeEl(), wrapper = makeEl();
  const storage = new Map();
  const localStorage = { getItem: (k) => storage.get(k) || null, setItem: (k, v) => storage.set(k, v), removeItem: (k) => storage.delete(k) };
  const requests = [];
  const win = Object.assign(makeEl(), { location: { origin: 'http://lab', search: '' } });
  const frappe = {
    boot: { scope_context_enabled: true, scope_context: { current: { company: 'C' }, hierarchy: { companies: [{ name: 'C' }], projects: [{ name: 'A', company: 'C' }] } } },
    pages: { 'execution-breakdown': {} },
    ui: { make_app_page: () => ({ main: root }) },
    dom: { set_style() {} },
    call: (opts) => {
      let resolve, reject;
      const p = new Promise((a, b) => { resolve = a; reject = b; });
      const record = { opts, resolve, reject };
      function jqueryPromise(promise) {
        return {
          then: (ok, err) => jqueryPromise(promise.then(ok, err)),
          fail: (fn) => { record.fail = fn; return this; },
          always: (fn) => jqueryPromise(promise.finally(fn)),
        };
      }
      const jq = jqueryPromise(p);
      record.jqueryPromise = jq;
      requests.push(record);
      return jq;
    },
    utils: { escape_html: String, icon: () => '', is_rtl: () => false },
    prompt() {},
    confirm() {},
  };
  function $(arg) {
    if (arg && (arg._isDom || arg.handlers || arg.delegated)) return arg;
    if (arg && arg.tag) return wrapDom(arg);
    return arg;
  }
  const context = vm.createContext({ window: win, document, localStorage, frappe, $, __: (x) => x, console, setTimeout });
  vm.runInContext(fs.readFileSync('construction/public/js/scope_context.js', 'utf8'), context);
  vm.runInContext(fs.readFileSync('construction/construction/page/execution_breakdown/execution_breakdown.js', 'utf8'), context);
  frappe.pages['execution-breakdown'].on_page_load(wrapper);

  win.scopeContext.setProject('A');
  confirm(requests[0]);
  const nodes = [
    { name: 'R1', title: 'Building', is_group: 1, parent_node: null, ebs_code: 'EBS-0001' },
    { name: 'C1', title: 'Floor', is_group: 1, parent_node: 'R1', ebs_code: 'EBS-0002' },
    { name: 'G1', title: 'Zone', is_group: 0, parent_node: 'C1', ebs_code: 'EBS-0003' },
    { name: 'C2', title: 'Roof', is_group: 0, parent_node: 'R1', ebs_code: 'EBS-0004' },
    { name: 'R2', title: 'External', is_group: 0, parent_node: null, ebs_code: 'EBS-0005' },
  ];
  requests[1].resolve({ message: { project: 'A', company: 'C', actions: { create: true, update: true }, nodes } });
  await tick();

  const body = root.find('[data-role="tree"]');
  body[0] = { contains: active => Boolean(active && active.treeOwned) };
  assert.equal((body.htmlValue.match(/tabindex="0"/g) || []).length, 1);
  assert.equal((body.htmlValue.match(/tabindex="-1"/g) || []).length, 4);
  assert.equal(body.htmlValue.includes('<ul class="tree-children" role="group"><ul class="tree-children"'), false);
  assert.equal(body.htmlValue.includes('<ul class="tree-children" role="group"></ul>'), false);
  assert.equal(root.htmlValue.includes('data-role="company"'), false);
  assert.equal(root.find('[data-role="company"]').textValue, '');

  function dispatchEvent(evType, targetEl, extra = {}) {
    const queue = [];
    for (let cur = targetEl; cur; cur = cur.parent) {
      for (const h of root.delegated) {
        if (h.ev === evType && matchesSelector(cur, h.selector)) {
          queue.push({ el: cur, fn: h.fn });
        }
      }
    }
    let stopped = false;
    const ev = Object.assign({ target: targetEl, stopPropagation() { stopped = true; }, preventDefault() {} }, extra);
    for (const item of queue) {
      if (stopped) break;
      item.fn.call(item.el, ev);
    }
  }

  // Click level-2 group C1 label -> collapses ONLY C1, keeping R1 open.
  let dom = parseHtml(body.htmlValue);
  let c1Label = findFirst(dom, (n) => n.tag === 'a' && n.attrs['data-name'] === 'C1');
  dispatchEvent('click', c1Label);
  dom = parseHtml(body.htmlValue);
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1').attrs['aria-expanded'], 'true');
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'C1').attrs['aria-expanded'], 'false');
  assert.equal(body.htmlValue.includes('1.1.1 Zone'), false);
  assert.equal(body.htmlValue.includes('1.1 Floor'), true);
  assert.equal(body.htmlValue.includes('1.2 Roof'), true);

  // Click level-2 group C1 icon (.node-parent) -> expands ONLY C1, keeping R1 open.
  const c1Icon = findFirst(dom, (n) => n.attrs['data-name'] === 'C1' && n.tag === 'span' && (n.attrs.class || '').includes('tree-link')).children[0];
  dispatchEvent('click', c1Icon);
  dom = parseHtml(body.htmlValue);
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1').attrs['aria-expanded'], 'true');
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'C1').attrs['aria-expanded'], 'true');
  assert.equal(body.htmlValue.includes('1.1.1 Zone'), true);

  // Click level-3 leaf G1 -> does NOT collapse C1 or R1.
  const g1Label = findFirst(dom, (n) => n.tag === 'a' && n.attrs['data-name'] === 'G1');
  dispatchEvent('click', g1Label);
  dom = parseHtml(body.htmlValue);
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1').attrs['aria-expanded'], 'true');
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'C1').attrs['aria-expanded'], 'true');

  // Click action button inside C1 -> does NOT collapse C1 or R1.
  const editBtn = findFirst(dom, (n) => n.tag === 'button' && n.attrs['data-action'] === 'edit' && n.attrs['data-name'] === 'C1');
  let actionKeyPrevented = false;
  dispatchEvent('keydown', editBtn, { key: 'ArrowDown', preventDefault() { actionKeyPrevented = true; } });
  assert.equal(actionKeyPrevented, false, 'tree navigation must not intercept action buttons');
  dispatchEvent('click', editBtn);
  dom = parseHtml(body.htmlValue);
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1').attrs['aria-expanded'], 'true');
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'C1').attrs['aria-expanded'], 'true');

  // Click empty padding inside R1's <ul class="tree-children"> -> does NOT collapse R1.
  const r1Item = findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1');
  const r1GroupUl = r1Item.children.find((n) => n.tag === 'ul');
  dispatchEvent('click', r1GroupUl);
  dom = parseHtml(body.htmlValue);
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1').attrs['aria-expanded'], 'true');

  // Keydown Enter and Space on C1 -> toggles ONLY C1 and refocuses C1.
  const c1Item = findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'C1');
  dispatchEvent('keydown', c1Item, { key: 'Enter' });
  assert.equal(focusedName, 'C1');
  dom = parseHtml(body.htmlValue);
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1').attrs['aria-expanded'], 'true');
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'C1').attrs['aria-expanded'], 'false');

  focusedName = null;
  const c1ItemCollapsed = findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'C1');
  dispatchEvent('keydown', c1ItemCollapsed, { key: ' ' });
  assert.equal(focusedName, 'C1');
  dom = parseHtml(body.htmlValue);
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1').attrs['aria-expanded'], 'true');
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'C1').attrs['aria-expanded'], 'true');

  // Keydown Enter on leaf G1 -> does NOT collapse C1 or R1.
  const g1Item = findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'G1');
  dispatchEvent('keydown', g1Item, { key: 'Enter' });
  dom = parseHtml(body.htmlValue);
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1').attrs['aria-expanded'], 'true');
  assert.equal(findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'C1').attrs['aria-expanded'], 'true');

  // Arrow navigation follows visible depth-first order, and Home/End reach its boundaries.
  function keyAt(name, key) {
    dom = parseHtml(body.htmlValue);
    const item = findFirst(dom, (n) => n.attrs.role === 'treeitem' && n.attrs['data-name'] === name);
    focusedName = null;
    dispatchEvent('keydown', item, { key });
    return focusedName;
  }
  assert.equal(keyAt('R1', 'ArrowDown'), 'C1');
  assert.equal(keyAt('G1', 'ArrowUp'), 'C1');
  assert.equal(keyAt('G1', 'Home'), 'R1');
  assert.equal(keyAt('R1', 'End'), 'R2');
  assert.equal(keyAt('C1', 'ArrowLeft'), 'C1'); // collapse and keep focus
  assert.equal(keyAt('C1', 'ArrowDown'), 'C2'); // hidden grandchild skipped
  assert.equal(keyAt('C1', 'ArrowRight'), 'C1'); // expand and keep focus
  assert.equal(keyAt('C1', 'ArrowRight'), 'G1'); // move to first child
  assert.equal(keyAt('G1', 'ArrowLeft'), 'C1'); // move to parent
  frappe.utils.is_rtl = () => true;
  assert.equal(keyAt('C1', 'ArrowRight'), 'C1'); // RTL collapse
  assert.equal(keyAt('C1', 'ArrowLeft'), 'C1'); // RTL expand
  frappe.utils.is_rtl = () => false;

  // Focus on a child hidden by a mouse collapse moves to the visible parent.
  document.activeElement = { treeOwned: true, getAttribute: key => ({role: 'treeitem', 'data-name': 'G1'})[key] };
  dom = parseHtml(body.htmlValue);
  const collapseRoot = findFirst(dom, n => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1');
  focusedName = null;
  dispatchEvent('click', collapseRoot);
  assert.equal(focusedName, 'R1');
  assert.equal((body.htmlValue.match(/tabindex="0"/g) || []).length, 1);

  // Rendering while an unrelated dialog control owns focus never steals it.
  const unrelated = { treeOwned: false, getAttribute: () => null };
  document.activeElement = unrelated;
  dom = parseHtml(body.htmlValue);
  const expandRoot = findFirst(dom, n => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1');
  focusedName = null;
  dispatchEvent('click', expandRoot);
  assert.equal(focusedName, null);
  assert.equal(document.activeElement, unrelated);

  // A same-Project refresh keeps focus only while the tree remains focused; a removed
  // node falls back to its surviving ancestor, and a user leaving during loading wins.
  document.activeElement = { treeOwned: true, getAttribute: key => ({role: 'treeitem', 'data-name': 'G1'})[key] };
  document.trigger('scope:changed');
  assert.equal(document.activeElement, body[0]);
  requests.at(-1).resolve({ message: { project: 'A', company: 'C', actions: {}, nodes: nodes.filter(n => n.name !== 'G1') } });
  await tick();
  assert.equal(focusedName, 'C1');
  document.activeElement = { treeOwned: true, getAttribute: key => ({role: 'treeitem', 'data-name': 'C1'})[key] };
  document.trigger('scope:changed');
  assert.equal(document.activeElement, body[0]);
  document.activeElement = unrelated;
  focusedName = null;
  requests.at(-1).resolve({ message: { project: 'A', company: 'C', actions: {}, nodes } });
  await tick();
  assert.equal(focusedName, null);
  assert.equal(document.activeElement, unrelated);

  // Refresh while an embedded Edit button owns focus restores that exact button.
  document.activeElement = {treeOwned: true, tagName: 'BUTTON', getAttribute: key => ({'data-action': 'edit', 'data-name': 'C1'})[key]};
  document.trigger('scope:changed');
  assert.equal(document.activeElement, body[0]);
  focusedAction = null;
  requests.at(-1).resolve({message: {project: 'A', company: 'C', actions: {update: true}, nodes}});
  await tick();
  assert.equal(focusedAction, 'edit');
  assert.equal(focusedName, 'C1');

  // If the action disappears, the owning tree item gets focus instead.
  document.activeElement = {treeOwned: true, tagName: 'BUTTON', getAttribute: key => ({'data-action': 'edit', 'data-name': 'C1'})[key]};
  document.trigger('scope:changed');
  focusedAction = 'sentinel';
  requests.at(-1).resolve({message: {project: 'A', company: 'C', actions: {}, nodes}});
  await tick();
  assert.equal(focusedAction, null);
  assert.equal(focusedName, 'C1');

  // Removed node falls back to its visible ancestor, and leaving while loading wins.
  document.activeElement = {treeOwned: true, tagName: 'BUTTON', getAttribute: key => ({'data-action': 'edit', 'data-name': 'C1'})[key]};
  document.trigger('scope:changed');
  requests.at(-1).resolve({message: {project: 'A', company: 'C', actions: {update: true}, nodes: nodes.filter(n => n.name !== 'C1' && n.name !== 'G1')}});
  await tick();
  assert.equal(focusedName, 'R1');
  assert.equal(focusedAction, null);
  document.activeElement = {treeOwned: true, tagName: 'BUTTON', getAttribute: key => ({'data-action': 'edit', 'data-name': 'R1'})[key]};
  document.trigger('scope:changed');
  document.activeElement = unrelated;
  focusedName = null;
  focusedAction = null;
  requests.at(-1).resolve({message: {project: 'A', company: 'C', actions: {update: true}, nodes}});
  await tick();
  assert.equal(focusedName, null);
  assert.equal(focusedAction, null);
  assert.equal(document.activeElement, unrelated);

  // Collapsing a parent hides the focused child action; focus moves to the parent.
  document.activeElement = {treeOwned: true, tagName: 'BUTTON', getAttribute: key => ({'data-action': 'edit', 'data-name': 'C1'})[key]};
  dom = parseHtml(body.htmlValue);
  const rootToCollapse = findFirst(dom, n => n.attrs.role === 'treeitem' && n.attrs['data-name'] === 'R1');
  dispatchEvent('click', rootToCollapse);
  assert.equal(focusedName, 'R1');
  assert.equal(focusedAction, null);
});
