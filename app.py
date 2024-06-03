import os
import threading
from flask import Flask, request, render_template, flash, redirect
from flask_sqlalchemy import SQLAlchemy
import yfinance as yf
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stocks.db'
db = SQLAlchemy(app)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(50), nullable=False)
    interval = db.Column(db.Integer, nullable=False, default=60)
    threshold = db.Column(db.Integer, nullable=False, default=2)

db.create_all()

@app.route('/')
def home():
    stocks = Stock.query.all()
    return render_template('index.html', stocks=stocks)

@app.route('/add_stock', methods=['POST'])
def add_stock():
    stock = request.form.get('stock')
    interval = int(request.form.get('interval'))
    threshold = int(request.form.get('threshold'))
    ticker = yf.Ticker(stock)
    try:
        ticker.history().tail(1)['Close'].iloc[0]
        new_stock = Stock(ticker=stock, interval=interval, threshold=threshold)
        db.session.add(new_stock)
        db.session.commit()
    except IndexError:
        flash('No stock found with that ticker.')
    return redirect('/')

@app.route('/update_stock/<int:id>', methods=['POST'])
def update_stock(id):
    stock = Stock.query.get_or_404(id)
    stock.interval = int(request.form.get('interval'))
    stock.threshold = int(request.form.get('threshold'))
    db.session.commit()
    return redirect('/')

@app.route('/check_stock_price')
def check_stock_price():
    def check_price():
        stocks = Stock.query.all()
        last_prices = {stock.ticker: 0 for stock in stocks}

        while True:
            for stock in stocks:
                try:
                    # Fetch current price
                    ticker = yf.Ticker(stock.ticker)
                    current_price = ticker.history().tail(1)['Close'].iloc[0]

                    # Check if the price has increased or decreased by the threshold in the last interval
                    if abs(current_price - last_prices[stock.ticker]) >= stock.threshold:
                        send_email(stock.ticker, current_price, current_price - last_prices[stock.ticker], stock.threshold, stock.interval)

                    # Update the last price
                    last_prices[stock.ticker] = current_price

                except Exception as e:
                    print(f"Error occurred while fetching the price for {stock.ticker}: {e}")

            # Wait for the specified interval
            time.sleep(stock.interval)

    thread = threading.Thread(target=check_price)
    thread.start()
    return redirect('/')

def send_email(stock, price, change, threshold, interval):
    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv('EMAIL')
        msg['To'] = os.getenv('EMAIL')
        msg['Subject'] = f'{stock} Stock Price Alert'
        direction = 'increased' if change > 0 else 'decreased'
        body = f'{stock} stock price has {direction} by ${threshold} in the last {interval} seconds. Current price is: ' + str(price)
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv('EMAIL'), os.getenv('PASSWORD'))
        text = msg.as_string()
        server.sendmail(os.getenv('EMAIL'), os.getenv('EMAIL'), text)
        server.quit()

    except Exception as e:
        print(f"Error occurred while sending the email: {e}")

if __name__ == '__main__':
    app.run(debug=True)
