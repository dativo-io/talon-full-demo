"""No provider required: mock model intent, assert all tools travel through the passed MCP boundary."""
import json
import unittest
from unittest.mock import patch

from agent_runtime import run_live_chat

TOOLS = [{'name':'hr_attrition_summary','description':'Aggregated attrition',
          'inputSchema': {'type':'object','properties':{'months':{'type':'integer'}}}}]
EXT = {'code':'allowed','decision':'allow','evidence':{'committed':True,'id':'test-receipt'}}


class LiveAgentTests(unittest.TestCase):
    def test_model_to_tool_to_model(self):
        requests = []
        def tool(name, arguments, session):
            requests.append((name,arguments,session))
            return 200, {'result': {'content':[{'type':'text','text':'{"attrition":2.1}'}],
                                    '_meta': {'io.dativo.talon/governance':EXT}}}
        response1={'choices':[{'message':{'role':'assistant','content':None,'tool_calls':[{
            'id':'call-1', 'type':'function',
            'function':{'name':'hr_attrition_summary','arguments':'{"months":6}'}}]}}]}
        response2={'choices':[{'message':{'role':'assistant','content':'Attrition is 2.1%, based on aggregate figures.'}}]}
        with patch('agent_runtime.chat_completion', side_effect=[response1,response2]) as gateway:
            result=run_live_chat('Attrition?',TOOLS,'hr-demo-test','gpt-4o-mini',
                                 'http://local-gateway','token',tool)
        self.assertEqual(result['answer'],'Attrition is 2.1%, based on aggregate figures.')
        self.assertEqual(requests,[('hr_attrition_summary',{'months':6},'hr-demo-test')])
        self.assertEqual(result['calls'][0]['governance']['evidence']['id'],'test-receipt')
        self.assertEqual(gateway.call_count,2)
        self.assertEqual(gateway.call_args_list[0].args[0],'http://local-gateway')
        self.assertEqual(gateway.call_args_list[0].args[3],'hr-demo-test')
        first_payload = gateway.call_args_list[0].args[2]
        self.assertEqual(first_payload['tool_choice'], 'required')
        self.assertEqual(first_payload['max_tokens'], 600)
        self.assertEqual(gateway.call_args_list[1].args[2]['tool_choice'], 'auto')


    def test_missing_receipt_does_not_reach_second_model_step(self):
        response={'choices':[{'message':{'role':'assistant','tool_calls':[{
            'id':'call-1','type':'function',
            'function':{'name':'hr_attrition_summary','arguments':'{}'}}]}}]}
        def ungoverned(name,arguments,session):
            return 200,{'result':{'content':[{'type':'text','text':'{"attrition":2.1}'}]}}
        with patch('agent_runtime.chat_completion',return_value=response) as gateway:
            with self.assertRaisesRegex(RuntimeError,'did not authorize'):
                run_live_chat('attrition',TOOLS,'hr-demo-test','m','local','token',ungoverned)
        self.assertEqual(gateway.call_count,1)

    def test_unauthorized_model_hallucination_never_calls_backend(self):
        response={'choices':[{'message':{'role':'assistant','tool_calls':[{
            'id':'call-1','type':'function',
            'function':{'name':'hr_employee_export','arguments':'{"scope":"all"}'}}]}}]}
        invoked=[]
        with patch('agent_runtime.chat_completion',return_value=response):
            with self.assertRaisesRegex(RuntimeError,'undiscovered tool'):
                run_live_chat('all data',TOOLS,'hr-demo-test','m','local','token',
                              lambda *args:invoked.append(args))
        self.assertFalse(invoked)

    def test_model_cannot_answer_analytics_without_governed_tool_result(self):
        response = {'choices':[{'message':{'role':'assistant',
                   'content':'Here are invented attrition figures.'}}]}
        with patch('agent_runtime.chat_completion', return_value=response) as gateway:
            with self.assertRaisesRegex(RuntimeError,'without fetching governed'):
                run_live_chat('attrition', TOOLS, 'hr-demo-test', 'm', 'local',
                              'token', lambda *args: self.fail('should not dispatch'))
        self.assertEqual(gateway.call_count, 1)

    def test_no_key_fails_without_calling_provider(self):
        with patch('agent_runtime.chat_completion') as gateway:
            with self.assertRaisesRegex(RuntimeError,'needs TALON_LLM_URL'):
                run_live_chat('hello',TOOLS,'hr-demo-test','m','','',None)
        gateway.assert_not_called()


if __name__=='__main__':
    unittest.main()
