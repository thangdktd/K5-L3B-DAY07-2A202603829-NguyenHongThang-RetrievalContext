"""Conservative deterministic paraphrase rules; synthetic fixtures, no API."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from grounding import verify_grounding
from openai_agent import validate_citation_format,validate_cited_answer,render_supported_claims

A='a'*64;B='b'*64

def chunk(cid,text):return {'id':cid,'text':text}

class GroundingRulesTests(unittest.TestCase):
    def check(self,claim,source,expected):
        result=verify_grounding(claim,source)
        self.assertEqual(result['passed'],expected,result)
        return result

    def test_verbatim_and_unicode_whitespace_punctuation(self):
        self.check('The valve opens.','The valve opens.',True)
        self.check('The valve opens; then stops.','The valve opens, then stops!',True)
        self.check('Cafe\u0301 remains open.','Caf\u00e9 remains\n open.',True)

    def test_audited_contractions_and_unit_aliases(self):
        self.check('The unit can not operate.','The unit cannot operate.',True)
        self.check('The unit must not operate.','The unit mustn\u2019t operate.',True)
        self.check('Wait 6 hr before starting.','Wait 6 hours before starting.',True)
        self.check('Use 10 millimeters of insulation.','Use 10 mm of insulation.',True)

    def test_adjacent_affirmative_sentences_joined_in_order(self):
        result=self.check('The sensor measures pressure and the display shows temperature.',
                          'The sensor measures pressure. The display shows temperature.',True)
        self.assertEqual(result['method'],'adjacent_affirmative_sentence_conjunction')
        self.check('The display shows pressure and the sensor measures temperature.',
                   'The sensor measures pressure. The display shows temperature.',False)

    def test_wrong_number_unit_sign_and_comparison_fail(self):
        for claim in ['Wait 8 hours before starting.','Wait 6 minutes before starting.',
                      'Wait -6 hours before starting.']:
            self.check(claim,'Wait 6 hours before starting.',False)
        self.check('Pressure must be > 5 bar.','Pressure must be < 5 bar.',False)
        self.check('Apply 10 MA.','Apply 10 mA.',False)
        self.check('Apply 10 mV.','Apply 10 MV.',False)

    def test_negation_reversal_and_dropped_negation_fail(self):
        self.check('The valve must open.','The valve must not open.',False)
        self.check('The valve must not open.','The valve must open.',False)
        self.check('Open the valve.','Do not open the valve.',False)

    def test_new_dropped_or_changed_conditions_fail(self):
        self.check('Open the valve when cold.','Open the valve.',False)
        self.check('Open the valve.','If pressure is low, open the valve.',False)
        self.check('If pressure is high, open the valve.','If pressure is low, open the valve.',False)
        self.check('Start before cooling.','Start after cooling.',False)

    def test_modal_strength_and_numeric_substring_not_relaxed(self):
        self.check('The unit must stop.','The unit may stop.',False)
        self.check('6 hours','36 hours',False)
        self.check('6 hours','-6 hours',False)
        self.check('6 hours','6 hours',True)

    def test_unknown_semantic_paraphrase_and_causal_inference_fail_closed(self):
        result=self.check('The controller allows adjustment.','Adjustment is possible.',False)
        self.assertEqual(result['reason'],'unverified_paraphrase_or_added_information')
        self.check('The button is present, allowing adjustment.',
                   'The button is present. Adjustment is possible.',False)
        self.check('The valve opens automatically.','The valve opens.',False)

    def test_math_symbols_and_questions_do_not_become_plain_assertions(self):
        self.check('Pressure is 5 bar.','Pressure is \u2264 5 bar.',False)
        self.check('Pressure is >= 5 bar.','Pressure is \u2265 5 bar.',True)
        self.check('Use 6 mm.','Use \u00b16 mm.',False)
        self.check('The valve opens.','The valve opens?',False)

    def test_bounds_uncertainty_and_recommendation_not_dropped(self):
        self.check('Pressure is 5 bar.','Maximum pressure is 5 bar.',False)
        self.check('Pressure is 5 bar.','Pressure is approximately 5 bar.',False)
        self.check('Use 5 bar.','Recommended use 5 bar.',False)

    def test_citation_validation_separate_from_grounding(self):
        rows=[chunk(A,'The valve closes.')]
        parsed,reason=validate_citation_format(f'The valve opens [{A}]',[A],rows)
        self.assertIsNone(reason);self.assertEqual(len(parsed),1)
        checks=[]
        self.assertFalse(validate_cited_answer(f'The valve opens [{A}]',[A],rows,checks)[0])
        self.assertFalse(checks[0]['passed'])
        for ids in [[],[B],['bad']]:
            checks=[]
            self.assertFalse(validate_cited_answer(f'The valve opens [{A}]',ids,rows,checks)[0])
            self.assertEqual(checks,[])

    def test_two_claims_two_sources_with_verified_equivalences(self):
        claims=[{'text':'Wait 6 hr before starting.','chunk_ids':[A]},
                {'text':'The unit can not operate.','chunk_ids':[B]}]
        checks=[]
        answer,ids,reason=render_supported_claims(claims,[chunk(A,'Wait 6 hours before starting.'),chunk(B,'The unit cannot operate.')],checks)
        self.assertIsNone(reason);self.assertEqual(ids,[A,B])
        self.assertTrue(all(c['passed'] for c in checks));self.assertIn(f'[{A}]',answer)

    def test_rejection_records_specific_reason_without_relaxing_it(self):
        checks=[]
        _,_,reason=render_supported_claims([{'text':'Wait 8 hours before starting.','chunk_ids':[A]}],
                                          [chunk(A,'Wait 6 hours before starting.')],checks)
        self.assertEqual(reason,'unsupported_cited_claim')
        self.assertEqual(checks[0]['reason'],'numeric_mismatch')

if __name__=='__main__':unittest.main()
