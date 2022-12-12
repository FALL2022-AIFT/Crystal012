import random
from realData import *
from pytrader import *

code = "0000" # 주식종목 코드

real_data = kiwoom.return_data(code)

def model(real_data):
    
    order_type = random.randint(0, 3)
    order_quantity = random.randint(0, 10)

    pyTrader(stock_account, order_type, code, order_quantity, 0, "03")
    return order_type

