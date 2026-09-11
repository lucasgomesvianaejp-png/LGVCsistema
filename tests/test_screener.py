import unittest
from engine.screener import PreScreenInput,pre_screen

class ScreenerTests(unittest.TestCase):
    def test_clear_fail_liquidity(self):
        r=pre_screen(PreScreenInput('AAA3','Industriais',500_000,0.08,10,False,5)); self.assertEqual(r.status,'FAIL'); self.assertIn('LIQUIDEZ_ABAIXO_MINIMO',r.fail_reasons)
    def test_clear_fail_dy(self):
        r=pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.04,10,False,5)); self.assertEqual(r.status,'FAIL'); self.assertIn('DY_5A_CLARAMENTE_ABAIXO_MINIMO',r.fail_reasons)
    def test_near_dy(self):
        r=pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.058,10,False,5)); self.assertEqual(r.status,'NEAR')
    def test_action_blocks_dy_fail(self):
        r=pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.02,10,True,5)); self.assertEqual(r.status,'NEAR'); self.assertNotIn('DY_5A_CLARAMENTE_ABAIXO_MINIMO',r.fail_reasons)
    def test_pass(self):
        self.assertEqual(pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.07,10,False,5)).status,'PASS')
    def test_negative_profit_needs_review(self):
        self.assertEqual(pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.07,-10,False,5)).status,'NEAR')

if __name__=='__main__': unittest.main()
