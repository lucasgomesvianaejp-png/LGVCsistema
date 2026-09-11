import unittest
from scripts.lgv_data.b3 import parse_cotahist_line

def put(buf,start,end,value):
    text=str(value); width=end-start+1; buf[start-1:end]=list(text[:width].ljust(width))
def put_num(buf,start,end,value):
    width=end-start+1; buf[start-1:end]=list(str(value).rjust(width,'0'))

def make_line(market='010',ticker='CMIG4'):
    b=list(' '*245)
    put(b,1,2,'01'); put(b,3,10,'20260908'); put(b,11,12,'02'); put(b,13,24,ticker); put(b,25,27,market)
    put(b,28,39,'CEMIG'); put(b,40,49,'PN N1'); put_num(b,109,121,1170); put_num(b,171,188,117000000); put_num(b,211,217,1); put(b,231,242,'BRCMIGACNPR3')
    return ''.join(b)

class B3ParserTests(unittest.TestCase):
    def test_equity_fixed_width(self):
        rec=parse_cotahist_line(make_line())
        self.assertIsNotNone(rec); self.assertEqual(rec['ticker'],'CMIG4'); self.assertAlmostEqual(rec['close'],11.70); self.assertAlmostEqual(rec['financialVolume'],1_170_000.00)
    def test_fractional_not_separate_series(self):
        self.assertIsNone(parse_cotahist_line(make_line('020','CMIG4F')))

if __name__=='__main__': unittest.main()
