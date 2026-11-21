// Executes the exact Code node sources from the export, not a parallel implementation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const w = JSON.parse(fs.readFileSync(path.join(__dirname, 'shopify-support.workflow.json'), 'utf8'));
const node = name => w.nodes.find(n => n.name === name);
const run = (name, input, previous={}) => new Function('$json','$','$execution',node(name).parameters.jsCode)(
  input, key=>({first:()=>({json:previous[key]})}), {id:'unit-1'}
).json;
let passed=0;
const check=(name,fn)=>{fn();passed++;console.log('PASS '+name)};
const sample=()=>run('Operator settings and sample',{});
const draft=(p, text)=>run('Review-only support result',{statusCode:200,body:{choices:[{message:{content:JSON.stringify(text)}}]}},{'Verify order and minimize':p});
const prepare=(body,extra={})=>{const q=sample();q.email.body=body;q.email.subject='';Object.assign(q.email,extra);return run('Prepare request',q)};
const order=(extra={})=>({name:'#1001',email:'buyer@example.test',test:true,displayFinancialStatus:'PAID',displayFulfillmentStatus:'UNFULFILLED',totalReceivedSet:{presentmentMoney:{amount:'1000.00',currencyCode:'EUR'}},totalRefundedSet:{presentmentMoney:{amount:'0.00',currencyCode:'EUR'}},...extra});
const response=(o)=>({statusCode:200,body:{data:{orders:{nodes:[o],pageInfo:{hasNextPage:false}}}}});
const verify=(p,r=response(order()))=>run('Verify order and minimize',r,{'Prepare request':p});
const recommendation=(issue,recommendation,amount=null,body='Thank you for contacting us. We will review your request.')=>({issue,recommendation,proposed_refund_eur:amount,draft:body});
check('sample is safe and inactive; stock nodes, only two HTTP calls, no mutation or send',()=>{
  assert.equal(w.active,false);assert.ok(w.nodes.every(n=>n.type.startsWith('n8n-nodes-base.')));
  const http=w.nodes.filter(n=>n.type==='n8n-nodes-base.httpRequest');
  assert.deepEqual(http.map(n=>n.name),['Read Shopify order','Draft through Talon']);
  assert.ok(http.every(n=>n.parameters.authentication==='genericCredentialType'&&n.parameters.options.redirect.redirect.followRedirects===false));
  assert.match(http[0].parameters.jsonBody,/query SupportOrder/);
  assert.doesNotMatch(http[0].parameters.jsonBody,/mutation|refundCreate/);
  assert.match(http[1].parameters.jsonBody,/\$json.facts/);
  assert.doesNotMatch(http[1].parameters.jsonBody,/requester|\.email|\.body/);
  assert.deepEqual(w.connections['Input verified?'].main.map(x=>x[0].node),['Read Shopify order','Manual review only']);
  assert.deepEqual(w.connections['Order verified?'].main.map(x=>x[0].node),['Draft through Talon','Manual review only']);
});
check('order status produces useful reviewed draft without raw customer details',()=>{
  const p=prepare('Where is order #1001? My email is buyer@example.test and IBAN PL61109010140000071219812874');
  const q=verify(p);assert.equal(q.ready,'yes');assert.deepEqual(Object.keys(q.facts).sort(),['financial_status','fulfillment_status','issue_hints','proposed_refund_eur']);
  assert.doesNotMatch(JSON.stringify(q.facts),/buyer|IBAN|1001|PL611/);
  const d=draft(q,recommendation('order_status','status_reply',null,'Your order is not yet fulfilled. We can check the next steps.'));
  assert.equal(d.status,'draft_ready_for_operator_review');assert.equal(d.message_sent,false);assert.equal(d.refund_execution,'unavailable');
});
check('unverified sender and ambiguous order stop before lookup',()=>{
  assert.equal(prepare('order #1001 status',{sender_verified:false}).ready,'no');
  assert.equal(prepare('where are #1001 and #1002?').ready,'no');
  assert.equal(prepare('Something unrelated #1001').ready,'no');
});
check('unauthorized, non-test, missing email, ambiguous or errored Shopify response stops before model',()=>{
  const p=prepare('order #1001 status');
  for(const o of [order({email:'other@example.test'}),order({email:null}),order({test:false}),order({name:'#1002'})])assert.equal(verify(p,response(o)).ready,'no');
  const q=response(order());q.body.data.orders.nodes.push(order());assert.equal(verify(p,q).ready,'no');
  const e=response(order());e.body.errors=[{message:'protected data'}];assert.equal(verify(p,e).ready,'no');
  assert.equal(verify(p,{statusCode:429,body:{}}).ready,'no');
});
check('amounts 25, 249, 750 are proposals only, never authorization',()=>{
 for(const amount of ['25','249','750']){
   const q=verify(prepare('Order #1001 refund EUR '+amount+' for damaged product'));
   assert.equal(q.facts.proposed_refund_eur,amount+'.00');
   const d=draft(q,recommendation('refund_request','refund_review',amount+'.00'));
   assert.equal(d.status,'draft_ready_for_operator_review');assert.equal(d.merchant_eligibility,'not_established');assert.equal(d.refund_execution,'unavailable');assert.equal(d.message_sent,false);
 }
});
check('within company amount band but exceeds observed balance: no refund proposal',()=>{
 const p=prepare('Order #1001 refund EUR 25');
 const q=verify(p,response(order({totalReceivedSet:{presentmentMoney:{amount:'20.00',currencyCode:'EUR'}}})));
 assert.equal(q.refund_screen,'manual_review');assert.equal(q.facts.proposed_refund_eur,null);
 assert.equal(draft(q,recommendation('refund_request','refund_review','25.00')).status,'manual_review');
 assert.equal(draft(q,recommendation('refund_request','manual_review')).status,'draft_ready_for_operator_review');
});
check('refund amount strict currency, status, exact proposal and no invented amount',()=>{
 const p=prepare('Order #1001 refund EUR 25');
 const q=verify(p);assert.equal(draft(q,recommendation('refund_request','refund_review','25.01')).status,'manual_review');
 assert.equal(draft(q,recommendation('refund_request','refund_review',25)).status,'manual_review');
 for(const o of [order({displayFinancialStatus:'REFUNDED'}),order({totalReceivedSet:{presentmentMoney:{amount:'1000',currencyCode:'USD'}}})])assert.equal(verify(p,response(o)).facts.proposed_refund_eur,null);
 assert.equal(verify(prepare('Order #1001 refund EUR 25 and EUR 249')).facts.proposed_refund_eur,null);
});
check('damaged, incorrect, returns and shipping delay classification hints',()=>{
 for(const [message,issue] of [['damaged product','damaged_product'],['wrong product','incorrect_product'],['return item','return_request'],['delay','shipping_delay']]){
 const q=verify(prepare('Order #1001 '+message));assert.ok(q.facts.issue_hints.includes(issue));
 assert.equal(draft(q,recommendation(issue,'manual_review')).status,'draft_ready_for_operator_review');
 }
});
check('model failure, invented success, PII and malformed response stop',()=>{
 const q=verify(prepare('Order #1001 refund EUR 25'));
 assert.equal(draft(q,recommendation('refund_request','refund_review','25.00','Your refund has been processed today.')).status,'manual_review');
 assert.equal(draft(q,recommendation('refund_request','refund_review','25.00','Contact buyer@example.test for help.')).status,'manual_review');
 const prev={'Verify order and minimize':q};
 for(const resp of [{statusCode:403,body:{}},{statusCode:200,body:{choices:[{message:{content:'not json'}}]}}])assert.equal(run('Review-only support result',resp,prev).status,'manual_review');
});
console.log('PASS '+passed+' Stage A contracts (Code node execution; not n8n or Talon runtime)');
