const test = require('node:test');
const assert = require('node:assert/strict');
const {selectLatestRequesterComment, validAdapterHostname, operatorMessageForError, errorBodyFrom} = require('../assets/main.js');
test('selects newest public requester comment', () => { const comments=[{public:true,author_id:9,plain_body:'agent'},{public:false,author_id:7,plain_body:'private'},{public:true,author_id:7,plain_body:'latest'},{public:true,author_id:7,plain_body:'older'}]; assert.equal(selectLatestRequesterComment(comments,7).plain_body,'latest'); });
test('returns null without public requester comment',()=>assert.equal(selectLatestRequesterComment([{public:false,author_id:7,plain_body:'x'}],7),null));
test('validates adapter hostname without accepting URL or local/IP targets', () => { assert.equal(validAdapterHostname('demo.example.com'), true); assert.equal(validAdapterHostname('https://demo.example.com'), false); assert.equal(validAdapterHostname('localhost'), false); assert.equal(validAdapterHostname('127.0.0.1'), false); assert.equal(validAdapterHostname('-bad.example.com'), false); });
test('maps adapter error codes to distinct operator actions', () => {
  assert.match(operatorMessageForError('policy_denied', false), /policy denied/i);
  assert.match(operatorMessageForError('rate_limited', true), /rate limiting/i);
  assert.match(operatorMessageForError('integration_misconfigured', false), /misconfigured/i);
  assert.match(operatorMessageForError('service_unavailable', true), /temporarily unavailable/i);
  // policy denial must never suggest a retry
  assert.doesNotMatch(operatorMessageForError('policy_denied', false), /try again|retry shortly/i);
  // unknown code falls back safely
  assert.match(operatorMessageForError('', false), /human agent/i);
});
test('extracts the adapter error body from a ZAF-style rejection', () => {
  assert.deepEqual(errorBodyFrom({responseJSON: {code: 'policy_denied', retryable: false}}), {code: 'policy_denied', retryable: false});
  assert.deepEqual(errorBodyFrom({responseText: '{"code":"rate_limited","retryable":true}'}).code, 'rate_limited');
  assert.equal(errorBodyFrom({responseText: 'not json'}), null);
  assert.equal(errorBodyFrom(null), null);
});
