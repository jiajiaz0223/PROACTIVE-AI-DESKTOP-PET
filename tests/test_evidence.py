import json,unittest
from unittest.mock import patch
from proactive_pet.ai.evidence import match_quote
from proactive_pet.ai.local_model import LocalModel

SOURCE='三十分鐘後在A辦公室參加設計師面試，請準備作品集。'
BROKEN='三十分鐘後在A辦公室參加設計師面試，請準備作品: 三十分鐘後在A辦公室參加設計師面試，請準備作品集'

class EvidenceTests(unittest.TestCase):
    def test_actual_user_failure_recovers_the_original_source(self):
        self.assertEqual(match_quote(SOURCE,BROKEN),SOURCE)
    def test_spacing_width_and_quote_marks(self):
        quote='「三十分鐘後在 A 辦公室參加設計師面試,請準備作品集。」'
        self.assertEqual(match_quote(SOURCE,quote),SOURCE)
    def test_partial_literal_quote_is_still_an_original_slice(self):
        source='通知：明天下午三點在Ａ辦公室面試。'
        result=match_quote(source,'明天下午三點在 A 辦公室面試')
        self.assertEqual(result,'明天下午三點在Ａ辦公室面試')
        self.assertIn(result,source)
    def test_changed_venue_time_or_negation_stay_unmatched(self):
        for evidence in [SOURCE.replace('A','B'),SOURCE.replace('三十分鐘','五十分鐘'),
                         SOURCE.replace('請準備','不用準備'),'',None,123]:
            self.assertIsNone(match_quote(SOURCE,evidence),repr(evidence))
        self.assertIsNone(match_quote('明天下午三點不用帶作品集','明天下午三點帶作品集'))
    def test_only_recover_full_source_not_a_fuzzy_fragment(self):
        self.assertIsNone(match_quote(SOURCE,'面試通知：請準備你的作品集，不然會遲到'))
    def test_pipeline_keeps_raw_model_quote_and_validates_event_time(self):
        client=LocalModel()
        proposal={'action':'create','title':'設計師面試','time':None,
                  'relative_minutes':30,'shift_minutes':None,'target_event_id':None,
                  'location':'A辦公室','preparations':['請準備作品集'],
                  'needs_review':False,'reason':'','evidence':BROKEN}
        source={'content':SOURCE,'timestamp':'2026-10-25T15:00:00+08:00','user_requested_event':True}
        with patch.object(client,'request',return_value={'message':{'content':json.dumps({'events':[proposal]})}}):
            result=client.analyze(source,[])[0]
        self.assertFalse(result['needs_review'])
        self.assertEqual(result['time'],'2026-10-25T15:30:00+08:00')
        self.assertEqual(result['evidence'],SOURCE)
        self.assertEqual(source['model_analysis']['raw_proposals'][0]['evidence'],BROKEN)

if __name__=='__main__':unittest.main()
