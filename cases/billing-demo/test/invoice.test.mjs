import assert from 'node:assert/strict';
import test from 'node:test';
import {invoiceTotal} from '../src/invoice.mjs';
test('rounds aggregate invoice total once', () => assert.equal(invoiceTotal([{unitPrice:0.333,quantity:1,taxRate:0},{unitPrice:0.333,quantity:1,taxRate:0},{unitPrice:0.333,quantity:1,taxRate:0}]),1.00));
