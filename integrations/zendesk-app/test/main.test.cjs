const test = require('node:test');
const assert = require('node:assert/strict');
const {selectLatestRequesterComment, validAdapterHostname} = require('../assets/main.js');
test('selects newest public requester comment', () => { const comments=[{public:true,author_id:9,plain_body:'agent'},{public:false,author_id:7,plain_body:'private'},{public:true,author_id:7,plain_body:'latest'},{public:true,author_id:7,plain_body:'older'}]; assert.equal(selectLatestRequesterComment(comments,7).plain_body,'latest'); });
test('returns null without public requester comment',()=>assert.equal(selectLatestRequesterComment([{public:false,author_id:7,plain_body:'x'}],7),null));
test('validates adapter hostname without accepting URL or local/IP targets', () => { assert.equal(validAdapterHostname('demo.example.com'), true); assert.equal(validAdapterHostname('https://demo.example.com'), false); assert.equal(validAdapterHostname('localhost'), false); assert.equal(validAdapterHostname('127.0.0.1'), false); assert.equal(validAdapterHostname('-bad.example.com'), false); });
