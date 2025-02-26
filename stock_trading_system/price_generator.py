import random

def update_stock_price(stock):
    change = random.uniform(-0.05, 0.05)
    new_price = round(stock.current_price * (1 + change), 2)
    if new_price > stock.high:
        stock.high = new_price
    if new_price < stock.low:
        stock.low = new_price
    stock.current_price = new_price
    return stock
