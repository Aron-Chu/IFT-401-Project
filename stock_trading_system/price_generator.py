import random
from datetime import datetime
from models import PriceHistory
from database import db

def update_stock_price(stock):
    fluctuation = random.uniform(-0.05, 0.05)
    new_price = round(stock.current_price * (1 + fluctuation), 2)

    if new_price > stock.high:
        stock.high = new_price
    if new_price < stock.low:
        stock.low = new_price

    stock.current_price = new_price

    price_record = PriceHistory(stock_id=stock.id, price=new_price)
    db.session.add(price_record)
    db.session.commit()
