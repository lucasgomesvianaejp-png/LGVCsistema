import unittest
from engine.lgv_engine import StockDecision, pc_lgv, required_yield, rank_opportunities, select_theoretical_portfolio


class LGVEngineTests(unittest.TestCase):
    def test_pc_is_minimum(self):
        self.assertEqual(pc_lgv(12.0, 10.0), 10.0)
        self.assertEqual(pc_lgv(8.0, 11.0), 8.0)

    def test_required_yield_bounds(self):
        self.assertEqual(required_yield(0.04), 0.06)
        self.assertAlmostEqual(required_yield(0.073), 0.078)
        self.assertEqual(required_yield(0.09), 0.08)

    def test_no_new_capital_above_pc(self):
        s = StockDecision('AAA3','Setor',8,8,10,12,10.01,'A',True)
        self.assertFalse(s.eligible_for_new_capital)
        self.assertEqual(s.price_status, 'RAZOAVEL')

    def test_audit_grade_blocks_purchase(self):
        s = StockDecision('AAA3','Setor',8,8,10,12,9,'B',True)
        self.assertFalse(s.eligible_for_new_capital)

    def test_opportunity_weight(self):
        s = StockDecision('AAA3','Setor',8,6,10,12,9,'A',True)
        self.assertAlmostEqual(s.opportunity_score, 7.3)

    def test_sector_limit(self):
        base = [
            StockDecision('A1','Banco',9,9,10,12,9),
            StockDecision('A2','Banco',8,8,10,12,9),
            StockDecision('A3','Banco',7,7,10,12,9),
            StockDecision('B1','Energia',8,8,10,12,9),
        ]
        selected = select_theoretical_portfolio(base)
        self.assertEqual([x.ticker for x in selected], ['A1','A2','B1'])

    def test_rank_is_deterministic(self):
        a = StockDecision('AAA3','S',8,8,10,12,9)
        b = StockDecision('BBB3','S',7,9,10,12,9)
        ranked = rank_opportunities([b,a])
        self.assertEqual(ranked[0].ticker, 'AAA3')


if __name__ == '__main__':
    unittest.main()
