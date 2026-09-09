from scripts.lgv_data.b3 import parse_cotahist_line


def put(buf, start, end, value):
    text = str(value)
    width = end - start + 1
    text = text[:width].ljust(width)
    buf[start-1:end] = list(text)


def put_num(buf, start, end, value):
    width = end - start + 1
    text = str(value).rjust(width, '0')
    buf[start-1:end] = list(text)


def test_parse_equity_cotahist_fixed_width():
    b = list(' ' * 245)
    put(b,1,2,'01')
    put(b,3,10,'20260908')
    put(b,11,12,'02')
    put(b,13,24,'CMIG4')
    put(b,25,27,'010')
    put(b,28,39,'CEMIG')
    put(b,40,49,'PN N1')
    put_num(b,57,69,1150)
    put_num(b,70,82,1200)
    put_num(b,83,95,1100)
    put_num(b,96,108,1160)
    put_num(b,109,121,1170)
    put_num(b,148,152,1234)
    put_num(b,153,170,100000)
    put_num(b,171,188,117000000)
    put_num(b,211,217,1)
    put(b,231,242,'BRCMIGACNPR3')
    rec = parse_cotahist_line(''.join(b))
    assert rec is not None
    assert rec['ticker'] == 'CMIG4'
    assert rec['close'] == 11.70
    assert rec['financial_volume'] == 1_170_000.00
    assert rec['market_type'] == 10


def test_fractional_market_is_not_separate_economic_series():
    b = list(' ' * 245)
    put(b,1,2,'01'); put(b,3,10,'20260908'); put(b,13,24,'CMIG4F')
    put(b,25,27,'020'); put(b,40,49,'PN N1'); put(b,231,242,'BRCMIGACNPR3')
    assert parse_cotahist_line(''.join(b)) is None
