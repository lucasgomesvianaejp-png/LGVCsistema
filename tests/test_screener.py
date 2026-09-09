from engine.screener import PreScreenInput, pre_screen


def test_clear_fail_liquidity():
    r = pre_screen(PreScreenInput('AAA3','Industriais',500_000,0.08,10,False,5))
    assert r.status == 'FAIL'
    assert 'LIQUIDEZ_ABAIXO_MINIMO' in r.fail_reasons


def test_clear_fail_dy_does_not_need_deep_research():
    r = pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.04,10,False,5))
    assert r.status == 'FAIL'
    assert 'DY_5A_CLARAMENTE_ABAIXO_MINIMO' in r.fail_reasons


def test_near_dy_is_monitored_not_discarded():
    r = pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.058,10,False,5))
    assert r.status == 'NEAR'
    assert 'DY_5A_ZONA_DE_APROXIMACAO' in r.near_reasons


def test_corporate_action_blocks_dy_elimination():
    r = pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.02,10,True,5))
    assert r.status == 'NEAR'
    assert 'AJUSTE_EVENTO_SOCIETARIO_NECESSARIO' in r.near_reasons
    assert 'DY_5A_CLARAMENTE_ABAIXO_MINIMO' not in r.fail_reasons


def test_pass_clean_case():
    r = pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.07,10,False,5))
    assert r.status == 'PASS'


def test_negative_reported_profit_requires_review_instead_of_blind_fail():
    r = pre_screen(PreScreenInput('AAA3','Industriais',2_000_000,0.07,-10,False,5))
    assert r.status == 'NEAR'
